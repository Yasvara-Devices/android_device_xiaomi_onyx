#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: 2026 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#
"""Post-extraction sanity checks for the onyx blob set.

Both checks exist because of real regressions that a blob sync introduced
silently and that only surfaced far from their cause at runtime:

1. **Dangling library reference.** A vendor config can name a shared library
   that we never ship. The loader logs one line and carries on degraded, so
   the build succeeds and the failure shows up as unrelated misbehaviour.
   OS3.0.305.0.WOLCNXM's ``video_system_specs.json`` added
   ``libqcodec2_psfilter.so`` / ``libqcodec2_srfilter.so`` to
   ``QC2CodecPlugins`` and ``libqcodec2_roiencfilter.so`` to
   ``QC2PreProcessingFilters`` -- the first two were simply not in
   ``proprietary-files.txt``, and the third does not exist in any Xiaomi
   image at all.

2. **Shadowed blob.** A ``PRODUCT_COPY_FILES`` entry in ``device.mk`` can
   write to the same destination as an extracted blob. The device copy wins,
   so re-extracting the blob has no effect on the device and the sync looks
   like it did nothing. ``vendor/etc/media_tuna_v0/video_system_specs.json``
   is shadowed exactly this way.

3. **Load-bearing property deleted as debug noise.** Some ``debug.*`` entries
   in ``properties/vendor.prop`` are not debug knobs. Dropping
   ``media.c2.hal.selection=aidl`` makes the framework select the HIDL Codec2
   HAL, which the AIDL-only QTI stores never register on -- every ``c2.qti.*``
   codec disappears and all video recording dies.

Run standalone, or let ``extract-files.py`` invoke it after an extract:

    ./validate-blobs.py            # warn only, exit 0
    ./validate-blobs.py --strict   # exit 1 on any finding
"""

import argparse
import json
import os
import re
import sys

DEVICE_DIR = os.path.dirname(os.path.abspath(__file__))
VENDOR_DIR = os.path.join(
    DEVICE_DIR, '..', '..', '..', 'vendor', 'xiaomi', 'onyx', 'proprietary'
)

# Configs that list shared libraries to dlopen, as {path: [json keys to scan]}.
# A key maps to either a list of strings or a dict of lists.
LIB_REF_CONFIGS = {
    'vendor/etc/media_tuna_v0/video_system_specs.json': [
        'QC2CodecPlugins',
        'QC2PreProcessingFilters',
        'QC2PostProcessingFilters',
    ],
}

# Directories a dlopen of a bare soname can resolve from, relative to the
# extracted blob root. System/APEX libs are out of scope -- we only police
# libraries that we are supposed to be shipping ourselves.
LIB_SEARCH_DIRS = ['vendor/lib64', 'vendor/lib', 'odm/lib64', 'odm/lib']


def strip_jsonc(text: str) -> str:
    """Drop // and /* */ comments; QTI ships JSON with comments."""
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'(?m)//.*$', '', text)
    return text


def collect_strings(node) -> list:
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        return [s for n in node for s in collect_strings(n)]
    if isinstance(node, dict):
        return [s for n in node.values() for s in collect_strings(n)]
    return []


def shipped_libs() -> set:
    libs = set()
    for d in LIB_SEARCH_DIRS:
        p = os.path.join(VENDOR_DIR, d)
        if os.path.isdir(p):
            libs.update(os.listdir(p))
    return libs


def check_dangling_lib_refs(overrides: dict) -> list:
    """Validate the config that actually ships.

    A ``device.mk`` override is often deliberate -- ``video_system_specs.json``
    is pinned to a minimal plugin list on purpose, because CN's list pulls in
    ``libqc2vppfilter.so`` and the ``c2.mi.filter.ps``/``.sr`` post-processing
    filters, which need a QConfig service this ROM does not register. Loading
    them takes out the whole codec store (``qconfig interface is null``,
    ``Codec2-FilterWrapper: plugin not OK: -19``) and with it every camera.
    So when a config is overridden, check the ``device/`` source -- validating
    the shadowed vendor copy would demand libraries we deliberately do not ship.
    """
    findings = []
    have = shipped_libs()
    if not have:
        print(
            f'  note: no extracted blobs under {VENDOR_DIR}, skipping lib checks',
            file=sys.stderr,
        )
        return findings

    for rel, keys in LIB_REF_CONFIGS.items():
        path = overrides.get(rel) or os.path.join(VENDOR_DIR, rel)
        if not os.path.exists(path):
            continue
        try:
            with open(path) as f:
                data = json.loads(strip_jsonc(f.read()))
        except (json.JSONDecodeError, OSError) as e:
            findings.append(f'{rel}: could not parse ({e})')
            continue

        # The interesting keys live under an arbitrary top-level object.
        refs = []
        for node in [data, *(v for v in data.values() if isinstance(v, dict))]:
            for k in keys:
                if k in node:
                    refs += collect_strings(node[k])

        for ref in sorted(set(refs)):
            if ref.endswith('.so') and ref not in have:
                findings.append(f'{rel}: references {ref}, which is not shipped')
    return findings


def check_shadowed_blobs():
    """Find PRODUCT_COPY_FILES destinations that collide with an extracted blob.

    Returns ``(notes, overrides)``. These are reported as *notes*, not
    warnings: overriding a blob is a legitimate technique here. What matters is
    knowing it happens, because a blob sync updating such a file has no effect
    on the device -- which is how a stale config can silently pair with new
    libraries.
    """
    notes, overrides = [], {}
    pf = os.path.join(DEVICE_DIR, 'proprietary-files.txt')
    mk = os.path.join(DEVICE_DIR, 'device.mk')
    if not (os.path.exists(pf) and os.path.exists(mk)):
        return notes, overrides

    blob_dests = set()
    with open(pf) as f:
        for line in f:
            line = line.split('#')[0].strip()
            if not line or line.startswith('-'):
                line = line.lstrip('-')
            if not line:
                continue
            entry = line.split('|')[0]
            # "src:dest" means the destination is the right-hand side.
            dest = entry.split(':')[-1]
            if dest:
                blob_dests.add(dest.lstrip('/'))

    with open(mk) as f:
        mk_text = f.read()
    for m in re.finditer(
        r'\$\(LOCAL_PATH\)/(\S+?):\$\(TARGET_COPY_OUT_(\w+)\)/(\S+)', mk_text
    ):
        src, partition, dest = m.group(1), m.group(2).lower(), m.group(3)
        full = f'{partition}/{dest}'
        if full in blob_dests:
            overrides[full] = os.path.join(DEVICE_DIR, src)
            notes.append(
                f'device.mk overrides extracted blob {full} '
                f'(from {src}) -- a blob sync cannot change it on device'
            )
    return notes, overrides


# Properties that must survive any cleanup pass, as {prop: (file, why)}.
REQUIRED_PROPS = {
    'media.c2.hal.selection': (
        'properties/vendor.prop',
        'aidl',
        'HalSelection.cpp defaults to "hidl"; the QTI Codec2 stores are AIDL-only, '
        'so unsetting this hides every c2.qti.* codec and kills video recording',
    ),
    'debug.stagefright.c2inputsurface': (
        'properties/vendor.prop',
        '-1',
        'CCodec::CreateInputSurface() only builds the AIDL GraphicBufferSource '
        'fallback at -1; otherwise it returns nullptr and MediaCodec retries over '
        'OMX, which this device does not ship',
    ),
}


def check_required_props() -> list:
    findings = []
    for prop, (rel, want, why) in REQUIRED_PROPS.items():
        path = os.path.join(DEVICE_DIR, rel)
        if not os.path.exists(path):
            continue
        got = None
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f'{prop}='):
                    got = line.split('=', 1)[1]
        if got is None:
            findings.append(f'{rel}: {prop} is missing (want {want}) -- {why}')
        elif got != want:
            findings.append(f'{rel}: {prop}={got}, want {want} -- {why}')
    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        '--strict', action='store_true', help='exit non-zero on any finding'
    )
    args = ap.parse_args()

    print('Validating onyx blob set...')
    notes, overrides = check_shadowed_blobs()
    findings = check_dangling_lib_refs(overrides)

    if findings:
        print('  WARN Dangling library references:')
        for f in findings:
            print(f'         - {f}')
    else:
        print('  OK   Dangling library references')

    prop_findings = check_required_props()
    if prop_findings:
        print('  WARN Load-bearing properties:')
        for f in prop_findings:
            print(f'         - {f}')
    else:
        print('  OK   Load-bearing properties')
    findings += prop_findings

    # Informational: overriding a blob is legitimate, but a sync cannot touch it.
    for n in notes:
        print(f'  NOTE {n}')

    if findings:
        print(f'\n{len(findings)} finding(s).')
        return 1 if args.strict else 0

    print('\nAll checks passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
