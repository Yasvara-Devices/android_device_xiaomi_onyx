#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
#
# SPDX-FileCopyrightText: 2024 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

import struct
from pathlib import Path

from extract_utils.fixups_blob import (
    BlobFixupCtx,
    File,
    blob_fixup,
    blob_fixups_user_type,
)
from extract_utils.fixups_lib import (
    lib_fixup_remove,
    lib_fixups,
    lib_fixups_user_type,
)
from extract_utils.main import (
    ExtractUtils,
    ExtractUtilsModule,
)
from extract_utils.tools import (
    llvm_objdump_path,
)
from extract_utils.utils import (
    run_cmd,
)

namespace_imports = [
    'hardware/qcom-caf/sm8750',
    'hardware/qcom-caf/wlan',
    'hardware/xiaomi',
    'vendor/qcom/opensource/commonsys/display',
    'vendor/qcom/opensource/commonsys-intf/display',
    'vendor/qcom/opensource/dataservices',
    'vendor/qcom/opensource/display',
    'device/xiaomi/onyx',
]


def lib_fixup_vendor_suffix(lib: str, partition: str, *args, **kwargs):
    return f'{lib}_{partition}' if partition == 'vendor' else None


lib_fixups: lib_fixups_user_type = {
    **lib_fixups,
    (
        'libagm',
        'libagmclient',
        'libagmmixer',
        'libar-acdb',
        'libar-gsl',
        'libats',
        'liblx-osal',
        'libvui_intf',
    ): lib_fixup_remove,
    # A17 libaudioclient links V5; Soong rejects mixing it with V4 in one
    # blob's deps, so V4 is installed via PRODUCT_PACKAGES instead.
    'android.media.audio.common.types-V4-cpp': lib_fixup_remove,
    (
        'vendor.qti.diaghal-V1-ndk',
        'vendor.qti.diaghal@1.0',
        'vendor.qti.hardware.wifidisplaysession_aidl-V1-ndk',
        'vendor.qti.hardware.wifidisplaysession_aidl-V2-ndk',
        'vendor.qti.ims.uceaidlservice-V1-ndk',
        'vendor.qti.ImsRtpService-V1-ndk',
        'vendor.qti.qccsyshal_aidl-V1-ndk',
        'vendor.qti.qccvndhal_aidl-V1-ndk',
    ): lib_fixup_vendor_suffix,
}


def blob_fixup_graphic_buffer_size(
    ctx: BlobFixupCtx,
    file: File,
    file_path: str,
    disassemble_symbols: [str],
    *args,
    **kwargs,
):
    for line in run_cmd(
        [
            llvm_objdump_path,
            f'--disassemble-symbols={",".join(disassemble_symbols)}',
            file_path,
        ]
    ).splitlines():
        line = line.split(maxsplit=5)
        if len(line) != 6:
            continue

        # The size of GraphicBuffer changed from 0x100 to 0xd30
        offset, _, instruction, register, value, _ = line
        if instruction == 'mov' and register[:-1] == 'w0' and value == '#0x100':
            with open(file_path, 'rb+') as f:
                f.seek(int(offset[:-1], 16))
                f.write(b'\x00\xa6\x81\x52')  # AArch64 mov w0, #0xd30


llvm_readelf_path = str(Path(llvm_objdump_path).with_name('llvm-readelf'))


def _elf_pt_loads(data: bytes) -> list[tuple[int, int, int, int]]:
    e_phoff = struct.unpack_from('<Q', data, 32)[0]
    e_phentsize, e_phnum = struct.unpack_from('<HH', data, 54)
    loads = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, _, p_offset, p_vaddr, _, p_filesz, p_memsz = struct.unpack_from(
            '<IIQQQQQ', data, off
        )
        if p_type == 1:
            loads.append((p_offset, p_vaddr, p_filesz, p_memsz))
    return loads


def _elf_va_to_foff(loads: list[tuple[int, int, int, int]], va: int) -> int:
    for p_offset, p_vaddr, p_filesz, _ in loads:
        if p_vaddr <= va < p_vaddr + p_filesz:
            return p_offset + (va - p_vaddr)
    raise RuntimeError(f'VA {va:#x} not mapped in any PT_LOAD file range')


def _elf_foff_to_va(loads: list[tuple[int, int, int, int]], foff: int) -> int:
    for p_offset, p_vaddr, p_filesz, _ in loads:
        if p_offset <= foff < p_offset + p_filesz:
            return p_vaddr + (foff - p_offset)
    raise RuntimeError(f'file offset {foff:#x} not mapped in any PT_LOAD')


def _encode_aarch64_b(src_va: int, target_va: int) -> bytes:
    diff = target_va - src_va
    assert diff % 4 == 0, f'unaligned branch diff {diff}'
    imm26 = (diff >> 2) & 0x03FFFFFF
    return struct.pack('<I', 0x14000000 | imm26)


def blob_fixup_elf_u32_symbol(
    ctx: BlobFixupCtx,
    file: File,
    file_path: str,
    symbol: str,
    new_val: int,
    *args,
    **kwargs,
):
    """Set an exported 4-byte .data log-level global (e.g. pal_log_lvl) to new_val."""
    out = run_cmd([llvm_readelf_path, '--dyn-syms', '--wide', file_path])
    sym_va = None
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 8 and parts[6] != 'UND' and parts[7] == symbol:
            sym_va = int(parts[1], 16)
            break
    if sym_va is None:
        raise RuntimeError(f'{file_path}: exported symbol {symbol!r} not found')

    with open(file_path, 'rb+') as f:
        data = f.read()
        loads = _elf_pt_loads(data)
        foff = _elf_va_to_foff(loads, sym_va)
        f.seek(foff)
        f.write(struct.pack('<I', new_val))


def blob_fixup_set_log_level_err_only(
    ctx: BlobFixupCtx,
    file: File,
    file_path: str,
    symbol: str,
    *args,
    **kwargs,
):
    """Patch setPalLogLevel/setAgmLogLevel so level=1 sets mask 0x1 (ERR only), not 0x3."""
    stub = run_cmd(
        [llvm_objdump_path, '-d', f'--disassemble-symbols={symbol}', file_path]
    )
    body_va = None
    for line in stub.splitlines():
        toks = line.split()
        if len(toks) >= 4 and toks[2] == 'b' and toks[3].startswith('0x'):
            body_va = int(toks[3], 16)
            break
    if body_va is None:
        raise RuntimeError(f'{file_path}: failed to resolve CFI target for {symbol}')

    body = run_cmd(
        [
            llvm_objdump_path,
            '-d',
            f'--start-address={body_va:#x}',
            f'--stop-address={body_va + 0x120:#x}',
            file_path,
        ]
    )
    insns = []
    for line in body.splitlines():
        toks = line.split()
        if len(toks) >= 4 and toks[0].endswith(':'):
            try:
                va = int(toks[0][:-1], 16)
                word = int(toks[1], 16)
            except ValueError:
                continue
            insns.append((va, word, toks[2], ' '.join(toks[3:])))

    eq_target = None
    for i in range(len(insns) - 1):
        _, _, m0, op0 = insns[i]
        _, _, m1, op1 = insns[i + 1]
        if m0 == 'cmp' and '#0x1' in op0 and m1 == 'b.eq':
            eq_target = int(op1.split()[0], 16)
            break
    if eq_target is None:
        raise RuntimeError(f'{file_path}: cmp #0x1 / b.eq not found in {symbol}')

    patch_va = None
    for va, word, m, op in insns:
        if eq_target <= va <= eq_target + 0x10 and m == 'mov' and 'w9,' in op:
            if word == 0x52800069:  # mov w9, #0x3
                patch_va = va
                break
            if word == 0x52800029:  # already mov w9, #0x1 (idempotent)
                return
    if patch_va is None:
        raise RuntimeError(
            f'{file_path}: mov w9, #0x3 not found at {eq_target:#x} in {symbol}'
        )

    with open(file_path, 'rb+') as f:
        data = f.read()
        loads = _elf_pt_loads(data)
        foff = _elf_va_to_foff(loads, patch_va)
        f.seek(foff)
        f.write(struct.pack('<I', 0x52800029))  # mov w9, #0x1


def blob_fixup_silence_log_by_string(
    ctx: BlobFixupCtx,
    file: File,
    file_path: str,
    needles: list[str],
    *args,
    **kwargs,
):
    """Silence specific hot-loop __android_log_print callsites by .rodata format string.

    Handles both direct `bl __android_log_*@plt` (-> `mov w0, #0`, ABI-safe) and Clang
    tail-merged `b <shared_log_trampoline>` (-> `b <bl_va + 4>`, skipping only the log).
    Idempotent across re-runs and immune to address shifts across HyperOS blob drops.
    """
    with open(file_path, 'rb') as f:
        data = f.read()
    loads = _elf_pt_loads(data)

    target_vas: dict[int, str] = {}
    for needle in needles:
        nb = needle.encode('utf-8')
        pos = data.find(nb)
        if pos < 0:
            raise RuntimeError(f'{file_path}: log string {needle!r} not found')
        while pos >= 0:
            s = pos
            while s > 0 and data[s - 1] != 0:
                s -= 1
            target_vas[_elf_foff_to_va(loads, s)] = needle
            pos = data.find(nb, pos + 1)

    disasm = run_cmd([llvm_objdump_path, '-d', file_path])
    insns: list[tuple[int, str, str]] = []
    for line in disasm.splitlines():
        t = line.lstrip()
        if ':' not in t:
            continue
        addr_s, rest = t.split(':', 1)
        if not addr_s or any(c not in '0123456789abcdefABCDEF' for c in addr_s):
            continue
        rest = rest.lstrip()
        toks = rest.split(None, 2)
        if len(toks) < 2 or len(toks[0]) != 8:
            continue
        va = int(addr_s, 16)
        mnem = toks[1]
        ops = toks[2].strip() if len(toks) >= 3 else ''
        insns.append((va, mnem, ops))

    va_to_idx = {va: i for i, (va, _, _) in enumerate(insns)}
    patches: list[tuple[int, bytes]] = []
    matched_needles: set[str] = set()

    reg_page: dict[str, int] = {}
    for i, (va, mnem, ops) in enumerate(insns):
        if mnem in ('bl', 'blr', 'ret', 'b'):
            reg_page.clear()
            continue
        str_va = None
        if mnem == 'adrp':
            p = [x.strip() for x in ops.split(',')]
            if len(p) >= 2:
                try:
                    reg_page[p[0]] = int(p[1].split()[0], 16)
                except ValueError:
                    pass
        elif mnem == 'add':
            p = [x.strip() for x in ops.split(',')]
            if len(p) >= 3 and p[1] in reg_page and p[2].startswith('#'):
                try:
                    off = int(p[2][1:].split()[0], 0)
                    str_va = reg_page[p[1]] + off
                except ValueError:
                    pass
        elif mnem == 'adr':
            p = [x.strip() for x in ops.split(',')]
            if len(p) >= 2:
                try:
                    str_va = int(p[1].split()[0], 16)
                except ValueError:
                    pass

        if str_va not in target_vas:
            continue
        needle = target_vas[str_va]
        # Scan forward up to 12 insns for the log call or tail-merged trampoline branch
        for j in range(i + 1, min(len(insns), i + 13)):
            c_va, c_mnem, c_ops = insns[j]
            if c_mnem == 'bl' and '<__android_log_' in c_ops:
                patches.append((c_va, struct.pack('<I', 0x52800000)))  # mov w0, #0
                matched_needles.add(needle)
                break
            if c_mnem == 'mov' and c_ops.startswith('w0, #0x0'):
                # Already patched to mov w0, #0 (idempotent)
                matched_needles.add(needle)
                break
            if c_mnem == 'b':
                try:
                    tgt = int(c_ops.split()[0], 16)
                except ValueError:
                    break
                # Check if tgt..tgt+3 insns enters a shared `bl __android_log_*@plt`
                t_idx = va_to_idx.get(tgt)
                if t_idx is not None:
                    # Already patched to land right after `bl __android_log_*`?
                    if t_idx > 0 and insns[t_idx - 1][1] == 'bl' and '<__android_log_' in insns[t_idx - 1][2]:
                        matched_needles.add(needle)
                        break
                    for k in range(t_idx, min(len(insns), t_idx + 4)):
                        k_va, k_mnem, k_ops = insns[k]
                        if k_mnem == 'bl' and '<__android_log_' in k_ops:
                            patches.append((c_va, _encode_aarch64_b(c_va, k_va + 4)))
                            matched_needles.add(needle)
                            break
                break
            if c_mnem in ('bl', 'blr', 'ret'):
                break

    missing = [n for n in needles if n not in matched_needles]
    if missing:
        raise RuntimeError(f'{file_path}: no log callsite matched for {missing}')

    if patches:
        with open(file_path, 'rb+') as f:
            for p_va, p_bytes in patches:
                f.seek(_elf_va_to_foff(loads, p_va))
                f.write(p_bytes)


DISPLAY_CONFIG_TAIL = Path(__file__).with_name('configs').joinpath(
    'display', 'displayconfig_tail.xml'
).read_text()

blob_fixups: blob_fixups_user_type = {
    (
        'odm/bin/hw/vendor.xiaomi.hw.touchfeature-service',
        'odm/lib64/libadaptivehdr.so',
        'odm/lib64/libcolortempmode.so',
        'odm/lib64/libdither.so',
        'odm/lib64/libflatmode.so',
        'odm/lib64/libhistprocess.so',
        'odm/lib64/libmiBrightness.so',
        'odm/lib64/libmiSensorCtrl.so',
        'odm/lib64/libpaperMode.so',
        'odm/lib64/librhytheyecare.so',
        'odm/lib64/libsdr2hdr.so',
        'odm/lib64/libsre.so',
        'odm/lib64/libtruetone.so',
        'odm/lib64/libvideomode.so',
        'vendor/lib64/hw/camera.qcom.so',
        'vendor/lib64/libgnss.so'
    ): blob_fixup()
        .replace_needed(
            'android.hardware.sensors-V2-ndk.so',
            'android.hardware.sensors-V3-ndk.so'
    ),

    'odm/bin/hw/vendor.xiaomi.sensor.citsensorservice.aidl': blob_fixup()
        .replace_needed(
            'android.hardware.graphics.common-V5-ndk.so',
            'android.hardware.graphics.common-V7-ndk.so'
        )
        .replace_needed(
            'android.hardware.sensors-V2-ndk.so',
            'android.hardware.sensors-V3-ndk.so'
        )
        .replace_needed(
            'libtinyxml2.so',
            'libtinyxml2-v34.so'
    ),

    (
        'odm/etc/camera/enhance_motiontuning.xml',
        'odm/etc/camera/motiontuning.xml'
    ): blob_fixup()
        .regex_replace('xml=version', 'xml version'),

    # Pentas's accidental-touch filter is an OSS kernel ABI, not a HAL mode:
    # the closed touchfeature HAL accepts modes 7/15 but never forwards either to
    # the THP driver on onyx. Without these the nodes stay root:root and the app
    # reports the filter as unavailable. Applied here rather than by hand because
    # the OS3.0.305.0.WOLCNXM blob drop silently reverted the previous edit.
    'odm/etc/init/vendor.xiaomi.hw.touchfeature-service.rc': blob_fixup()
        .regex_replace(
            r'(    chmod 0664 /sys/class/touch/touch_dev/fod_press_status\n)',
            r'\1'
            '    chown system system /sys/class/touch/touch_dev/gamespace_touch_profile\n'
            '    chmod 0664 /sys/class/touch/touch_dev/gamespace_touch_profile\n'
            '    chown system system /sys/class/touch/touch_dev/gamespace_touch_capabilities\n'
            '    chmod 0644 /sys/class/touch/touch_dev/gamespace_touch_capabilities\n'
            '    chown system system /sys/class/touch/touch_dev/gamespace_touch_stats\n'
            '    chmod 0644 /sys/class/touch/touch_dev/gamespace_touch_stats\n',
    ),

    # THP tuning. `ic_rate_game` is the NT38771's physical scan rate and is
    # hard-capped at 240 (writing 300/480/960 to /proc/xm_htc_report_rate all read
    # back 240); `rate_game` is what the HAL emits to evdev, and 480 is a 2x
    # interpolation of that 240 Hz scan. 480 is the ceiling — 960 is rejected and
    # falls the pipeline back to 240. Measured on device: median inter-report
    # interval 4.16 ms -> 2.08 ms, and dynamic_fps_report=0 lifts the sustained
    # average from 378 Hz to 425 Hz by not scaling the rate down with app FPS.
    # zone_corner_...=200000 suppresses a stationary corner contact after 200 ms
    # and re-detects it as a new one, which is the MLBB analog "releases by
    # itself" bug; 1 s is long enough that a moving thumb never trips it.
    (
        'odm/firmware/o10u_nova_csot_thp_config.ini',
        'odm/firmware/o10u_nova_tm_thp_config.ini'
    ): blob_fixup()
        .regex_replace(r'(?m)^(\s*)rate_game=240$', r'\g<1>rate_game=480')
        .regex_replace(
            r'(?m)^(\s*)dynamic_fps_report=1$',
            r'\g<1>dynamic_fps_report=0',
        )
        .regex_replace(
            r'(?m)^(\s*)zone_corner_report_time_limit_after_move=200000$',
            r'\g<1>zone_corner_report_time_limit_after_move=1000000',
        )
        # Shrink the always-on landscape game edge strips and corner hold-off for
        # onyx's flat 447 ppi panel (~1.1 mm strips, ~2.3 mm corners). Stock
        # 60/70/100 px zones are sized for curved panels and overlap game HUD
        # buttons (25-51 px from the bezel), delaying taps 41-79 ms even with
        # mode 7 (edge filter) set to 0. Pentas Low/Mid/High (cornerfilter_area_step*)
        # remains intact.
        .regex_replace(
            r'(?m)^(\s*)game_long_side_for_horizon=60$',
            r'\g<1>game_long_side_for_horizon=20',
        )
        .regex_replace(
            r'(?m)^(\s*)game_short_size_for_horizon=70$',
            r'\g<1>game_short_size_for_horizon=20',
        )
        .regex_replace(
            r'(?m)^(\s*)game_new_corner_size=100$',
            r'\g<1>game_new_corner_size=40',
        )
        # Pentas's Fast touch response, the base the HAL's mode 206 widens from for
        # Stable. Kalman prediction is what overshoots a flick (8.6 px -> ~1 px); no
        # HAL mode reaches it. Numbers in lab/touch-stutter/README.md.
        .regex_replace(r'(?m)^(\s*)kalman_predict_en=1$', r'\g<1>kalman_predict_en=0')
        .regex_replace(r'(?m)^(\s*)move_jitter_lock_dis=6$', r'\g<1>move_jitter_lock_dis=3')
        .regex_replace(
            r'(?m)^(\s*)stable_jitter_lock_dis_game_mode=10$',
            r'\g<1>stable_jitter_lock_dis_game_mode=5',
        )
        .regex_replace(
            r'(?m)^(\s*)first_jitter_lock_dis_game_mode=30$',
            r'\g<1>first_jitter_lock_dis_game_mode=15',
        )
        .regex_replace(
            r'(?m)^(\s*)first_jitter_stable_frame_game_mode=36$',
            r'\g<1>first_jitter_stable_frame_game_mode=18',
        )
        .regex_replace(r'(?m)^(\s*)fod_area_overlap=40$', r'\g<1>fod_area_overlap=30')
        .regex_replace(r'(?m)^(\s*)fod_peak_thd=150$', r'\g<1>fod_peak_thd=120'),

    # The SR table in MISR::MISR, at the scales the SM8735 models were built for: stock keeps these
    # for one product name, and the default table asks for models only the SM8750 has.
    'vendor/lib64/libmialgo.so': blob_fixup()
        .binary_regex_replace(
            bytes.fromhex('80020000800100000300000001000000'),
            bytes.fromhex('80020000800100000500000001000000'),
        )
        .binary_regex_replace(
            bytes.fromhex('c0030000200200000200000001000000'),
            bytes.fromhex('c0030000200200000300000001000000'),
        )
        .binary_regex_replace(
            bytes.fromhex('80010000800200000300000000000000'),
            bytes.fromhex('80010000800200000500000000000000'),
        )
        .binary_regex_replace(
            bytes.fromhex('20020000c00300000200000000000000'),
            bytes.fromhex('20020000c00300000300000000000000'),
        ),
    'odm/lib64/camera/components/com.mi.node.tsskinbeautifier.so': blob_fixup()
        .call(
            blob_fixup_graphic_buffer_size,
            [
                'ChiNodeEntry',
            ],
        ),

    (
        'odm/lib64/camera/plugins/com.xiaomi.plugin.anchor.so',
        'odm/lib64/camera/plugins/com.xiaomi.plugin.offlineawbideal.so',
        'odm/lib64/camera/plugins/com.xiaomi.plugin.offlineb2y.so',
        'odm/lib64/camera/plugins/com.xiaomi.plugin.offlineformatconvertor.so',
        'odm/lib64/camera/plugins/com.xiaomi.plugin.offlinehdrraw2y.so',
        'odm/lib64/camera/plugins/com.xiaomi.plugin.offlineheic.so',
        'odm/lib64/camera/plugins/com.xiaomi.plugin.offlinei2y.so',
        'odm/lib64/camera/plugins/com.xiaomi.plugin.offlinejpeg.so',
        'odm/lib64/camera/plugins/com.xiaomi.plugin.offlinemfnr.so',
        'odm/lib64/camera/plugins/com.xiaomi.plugin.offlinemlawb.so',
        'odm/lib64/camera/plugins/com.xiaomi.plugin.offlinetintless.so',
        'odm/lib64/camera/plugins/com.xiaomi.plugin.offlinetintlesshdr.so',
        'odm/lib64/camera/plugins/com.xiaomi.plugin.offlineyuvreprocess.so',
        'odm/lib64/camera/plugins/com.xiaomi.plugin.offlineyuvsplit.so',
        'odm/lib64/libmiXmlParser.so',
        'vendor/bin/hw/vendor.qti.camera.provider-service_64',
        'vendor/bin/hw/vendor.qti.hardware.display.composer-service',
        'vendor/bin/poweropt-service',
        'vendor/lib64/libaodoptfeature.so',
        'vendor/lib64/libapengine.so',
        'vendor/lib64/libaudiocloudctrl.so',
        'vendor/lib64/libcamxcoreutils.so',
        'vendor/lib64/libcamxods.so',
        'vendor/lib64/liblearningmodule.so',
        'vendor/lib64/libmicamera_aidl_provider.so',
        'vendor/lib64/libpowercore.so',
        'vendor/lib64/libpsmoptfeature.so',
        'vendor/lib64/libsdmclient.so',
        'vendor/lib64/libsimulation.so',
        'vendor/lib64/libstandbyfeature.so',
        'vendor/lib64/soundfx/libquasar.so'
    ): blob_fixup()
        .replace_needed(
            'libtinyxml2.so',
            'libtinyxml2-v34.so'
    ),

    'odm/lib64/camera/plugins/com.xiaomi.plugin.beautydeformation.so': blob_fixup()
        .call(
            blob_fixup_graphic_buffer_size,
            [
                '_ZN23BeautyDeformationPlugin13processBufferEP11ImageParamsS1_S1_NSt3__110shared_ptrI10MiMetadataEES1_S1_',
            ],
        ),

    'odm/lib64/camera/plugins/com.xiaomi.plugin.filter.so': blob_fixup()
        .call(
            blob_fixup_graphic_buffer_size,
            [
                '_ZN12FilterPlugin14processRequestEP18ProcessRequestInfo',
            ],
        ),

    (
        'odm/lib64/camera/plugins/com.xiaomi.plugin.gainmap.so',
        'odm/lib64/camera/plugins/com.xiaomi.plugin.jpegrAggr.so'
    ): blob_fixup()
        .replace_needed(
            'libultrahdr.so',
            'libultrahdr_prebuilt.so'
    ),

    'odm/lib64/camera/plugins/com.xiaomi.plugin.skinbeautifierpreview.so': blob_fixup()
        .call(
            blob_fixup_graphic_buffer_size,
            [
                '_ZN27SkinBeautifierPreviewPlugin13processBufferEP11ImageParamsS1_NSt3__110shared_ptrI10MiMetadataEEP18ProcessRequestInfo',
            ],
        ),

    'odm/lib64/camera/plugins/com.xiaomi.plugin.tsskinbeautifier.so': blob_fixup()
        .call(
            blob_fixup_graphic_buffer_size,
            [
                '_ZN20SkinBeautifierPlugin13processBufferEP11ImageParamsS1_NSt3__110shared_ptrI10MiMetadataEES1_S1_',
            ],
        ),

    'odm/lib64/hw/displayfeature.default.so': blob_fixup()
        .replace_needed(
            'android.hardware.sensors-V2-ndk.so',
            'android.hardware.sensors-V3-ndk.so'
        )
        .replace_needed(
            'libtinyxml2.so',
            'libtinyxml2-v34.so'
    ),

    'odm/lib64/libdynamicelvss.so': blob_fixup()
        .replace_needed(
            'android.hardware.sensors-V2-ndk.so',
            'android.hardware.sensors-V3-ndk.so'
    ),

    (
        'odm/lib64/libAncHumanPreviewBokeh.so',
        'odm/lib64/libMiEmojiEffect.so',
        'odm/lib64/libMiVideoFilter.so',
        'odm/lib64/libTrueSight.so',
        'odm/lib64/libwa_widelens_undistort.so',
        'vendor/lib64/libMiPhotoFilter.so'
    ): blob_fixup()
        .clear_symbol_version('AHardwareBuffer_allocate')
        .clear_symbol_version('AHardwareBuffer_describe')
        .clear_symbol_version('AHardwareBuffer_isSupported')
        .clear_symbol_version('AHardwareBuffer_lock')
        .clear_symbol_version('AHardwareBuffer_lockPlanes')
        .clear_symbol_version('AHardwareBuffer_release')
        .clear_symbol_version('AHardwareBuffer_unlock'),

    (
        'odm/lib64/libaudioroute_ext.so',
        'vendor/lib64/libagm.so',
        'vendor/lib64/libar-pal.so',
        'vendor/lib64/libmcs.so',
        'vendor/lib64/libmikaraoke.so',
        'vendor/lib64/libtiantongpal.so'
    ): blob_fixup()
        .replace_needed(
            'libaudioroute.so',
            'libaudioroute-v34.so'
    ),

    'system_ext/etc/vintf/manifest/vendor.qti.qesdsys.service.xml': blob_fixup()
        .regex_replace(r'(?s)^.*?(?=<manifest)', ''),

    # Calls ion_close without NEEDing libion; A16's libdmabufheap used to
    # provide it. A17 libion is a stub (ION is gone on GKI), which is enough.
    'odm/lib64/anc.hal.so': blob_fixup()
        .add_needed('libion.so'),

    # A17 moved AudioSystem out of libaudioclient into libaudiobase.
    'system_ext/lib64/libwfdmmsrc_system.so': blob_fixup()
        .add_needed('libgui_shim.so')
        .add_needed('libaudiobase.so'),

    'system_ext/lib64/libwfdnative.so': blob_fixup()
        .add_needed('libbinder_shim.so')
        .add_needed('libinput_shim.so')
        .remove_needed('android.hidl.base@1.0.so'),

    'vendor/bin/nv_mac': blob_fixup()
        # Bypass libqcrilNrFramework/QtiSharedMutex __cxa_finalize SIGSEGV on exit:
        # replace main()'s `autiasp; ret` (with w0=0) with `mov x8, #94; svc #0` (exit_group(0)).
        .sig_replace(
            'fd 7b 45 a9 ff 43 02 91 bf 23 03 d5 c0 03 5f d6',
            'fd 7b 45 a9 ff 43 02 91 c8 0b 80 d2 01 00 00 d4',
        ),

    'vendor/bin/system_dlkm_modprobe.sh': blob_fixup()
        .regex_replace(
            r'for kernel_ver_dir in \$\{system_dlkm_dir\}/\*;',
            'for kernel_ver_dir in ${system_dlkm_dir} ${system_dlkm_dir}/*;',
        ),

    'vendor/etc/clstc_config_library.xml': blob_fixup()
        .regex_replace(r'<library>\s*<name>libdolbyclstc[\s\S]*?</library>', ''),

    (
        'vendor/etc/displayconfig/display_id_4630947173316895379.xml',
        'vendor/etc/displayconfig/display_id_4630947258895476883.xml',
    ): blob_fixup()
        # Keep stock's map and HDR ratios: the HAL remaps brightness assuming them. The tail holds
        # ramps and stock's lux hysteresis, see lab/display-hal/tools/gen_displayconfig_tail.py.
        .regex_replace(
            r'<screenBrightnessMap>',
            '<screenBrightnessMap interpolation="linear">',
        )
        # The ring buffer clamps old samples to this horizon, so it must exceed the debounce.
        .regex_replace(
            r'<ambientLightHorizonLong>\d+</ambientLightHorizonLong>',
            '<ambientLightHorizonLong>2500</ambientLightHorizonLong>',
        )
        .regex_replace(
            r'<ambientLightHorizonShort>\d+</ambientLightHorizonShort>',
            '<ambientLightHorizonShort>500</ambientLightHorizonShort>',
        )
        .regex_replace(r'</displayConfiguration>', DISPLAY_CONFIG_TAIL + '</displayConfiguration>'),

    'vendor/etc/sensors/hals.conf': blob_fixup()
        .regex_replace('.*vl53l8.*\n?', ''),

    'vendor/lib64/android.hardware.bluetooth.audio-impl_prebuilt.so': blob_fixup()
        .replace_needed(
            'libbluetooth_audio_session_aidl.so',
            'libbluetooth_audio_session_aidl_prebuilt.so'
    ),

    (
        'vendor/lib64/camera/components/com.qti.node.dewarp.so',
        'vendor/lib64/hw/com.qti.chi.override.so',
        'vendor/lib64/libcamximageformatutils.so',
        'vendor/lib64/libchifeature2.so',
        'vendor/lib64/libqvrservice.so',
        'vendor/lib64/vendor.qti.hardware.camera.offlinecamera-service-impl.so'
    ): blob_fixup()
        .replace_needed(
            'android.hardware.graphics.allocator-V1-ndk.so',
            'android.hardware.graphics.allocator-V2-ndk.so'
    ),

    (
        'vendor/lib64/hw/android.hardware.bluetooth.audio_sw.so',
        'vendor/lib64/libaudio_aidl_conversion_common_ndk_prebuilt.so'
    ): blob_fixup()
        .replace_needed(
            'android.media.audio.common.types-V6-ndk.so',
            'android.media.audio.common.types-V3-ndk.so'
    ),

    'vendor/lib64/hw/libaudioeffecthal.qti.so': blob_fixup()
        .replace_needed(
            'android.media.audio.common.types-V6-ndk.so',
            'android.media.audio.common.types-V3-ndk.so'
        )
        .replace_needed(
            'libtinyxml2.so',
            'libtinyxml2-v34.so'
    ),

    (
        'vendor/lib64/libVoiceSdk.so',
        'vendor/lib64/libcapiv2uvvendor.so',
        'vendor/lib64/liblistensoundmodel2vendor.so'
    ): blob_fixup()
        .replace_needed(
            'libtensorflowlite_c.so',
            'libtensorflowlite_c_vendor.so'
    ),

    'vendor/lib64/libaudioserviceexampleimpl.so': blob_fixup()
        .add_needed('libaudioutils_shim.so')
        .replace_needed(
            'android.hardware.bluetooth.audio-impl.so',
            'android.hardware.bluetooth.audio-impl_prebuilt.so'
        )
        .replace_needed(
            'libbluetooth_audio_session_aidl.so',
            'libbluetooth_audio_session_aidl_prebuilt.so'
        )
        .replace_needed(
            'libaudio_aidl_conversion_common_ndk.so',
            'libaudio_aidl_conversion_common_ndk_prebuilt.so'
        )
        .replace_needed(
            'android.media.audio.common.types-V6-ndk.so',
            'android.media.audio.common.types-V3-ndk.so'
    ),

    'vendor/lib64/libcameraopt.so': blob_fixup()
        .add_needed('libprocessgroup_shim.so'),

    'vendor/lib64/libcom.xiaomi.grallocutils.so': blob_fixup()
        .call(
            blob_fixup_graphic_buffer_size,
            [
                '_Z21allocateGraphicBufferjjim',
                '_Z29createGraphicBufferFromHandlejjimjPK13native_handle',
                '_ZN12GrallocUtils19createGrallocBufferEjjimjPK13native_handleP16GrallocBufHandle',
            ],
        ),

    'vendor/lib64/libcom.xiaomi.mawutils.so': blob_fixup()
        .call(
            blob_fixup_graphic_buffer_size,
            [
                '_ZN18MAWBufferAllocator18AllocGraphicBufferEjjijPPcRi',
            ],
        ),

    'vendor/lib64/libgpu_tonemapper.so': blob_fixup()
        .call(
            blob_fixup_graphic_buffer_size,
            [
                '_ZN15EGLImageWrapper4wrapEPKv',
            ],
        ),

    'vendor/lib64/libmicamera_hal_core.so': blob_fixup()
        .replace_needed(
            'libtinyxml2.so',
            'libtinyxml2-v34.so',
        )
        .call(
            blob_fixup_graphic_buffer_size,
            [
                '_ZN5mihal11ImageBufferC2EjjimNSt3__112basic_stringIcNS1_11char_traitsIcEENS1_9allocatorIcEEEE',
                '_ZN5mihal11ImageBufferC2EjjimPK13native_handle',
                '_ZN5mihal7SessionC2ERKNS0_10CreateInfoE',
                '_ZN5mihal12StreamWraper14requestBuffersEjRNSt3__16vectorIPNS_18StreamBufferWraperENS1_9allocatorIS4_EEEE',
                '_ZThn8_N5mihal12VendorCamera19getStreamByStreamIdEi',
            ],
        ),

    # MiuiCamera port: neutralize two `bl abort` calls by branching to the
    # function epilogue instead, and bypass the `get InternalStreamConfigInfo failed`
    # `__android_log_assert` in `DeviceSessionPolicy::buildVendorConfiguration`
    # while reloading x21 (`ldr x21, [x20, #0x88]; b 0x43f14`).
    'vendor/lib64/libmicamera_hal_policy.so': blob_fixup()
        .sig_replace('e4 03 15 2a e5 03 16 2a b2 b1 02 94', 'e403152a954640f901000014')
        .sig_replace('e4 73 00 94 01 74 00 94', 'e473009462ffff17')
        .sig_replace('be 20 00 94 db 20 00 94', 'be20009458ffff17'),

    'vendor/lib64/libqcodec2_core.so': blob_fixup()
        .add_needed('libcodec2_shim.so')
        .replace_needed(
            'android.hardware.graphics.common-V5-ndk.so',
            'android.hardware.graphics.common-V7-ndk.so'
        )
        .call(
            blob_fixup_silence_log_by_string,
            ['[%s] Skipping empty output buffer'],
            need_tmp_dir=False,
        ),

    'vendor/lib64/libqcrilNrVoiceModule.so': blob_fixup()
        .sig_replace('a1 00 80 52 22', 'a1 00 80 52 02'),

    'vendor/lib64/libultrahdr_prebuilt.so': blob_fixup()
        .replace_needed(
            'libjpegdecoder.so',
            'libjpegdecoder_prebuilt.so'
        )
        .replace_needed(
            'libjpegencoder.so',
            'libjpegencoder_prebuilt.so'
    ),

    'vendor/lib64/libwfdmmsrc_proprietary.so': blob_fixup()
        .replace_needed(
            'android.media.audio.common.types-V2-ndk.so',
            'android.media.audio.common.types-V3-ndk.so'
    ),

    (
        'vendor/lib64/soundfx/libbundleaidl.so',
        'vendor/lib64/soundfx/libhwdapaidl.so',
        'vendor/lib64/soundfx/libmiwndnsprocessingaidl.so'
    ): blob_fixup()
        .replace_needed(
            'android.media.audio.common.types-V6-ndk.so',
            'android.media.audio.common.types-V3-ndk.so'
        )
        .replace_needed(
            'libaudio_aidl_conversion_common_ndk.so',
            'libaudio_aidl_conversion_common_ndk_prebuilt.so'
    ),

    'vendor/lib64/vendor.libdpmframework.so': blob_fixup()
        .add_needed('libhidlbase_shim.so'),

    # Silence repetitive vendor/Xiaomi D/I/W logcat spam (keeps all ERROR logs intact).
    # Implemented as dynamic symbol/string-driven fixups so they survive HyperOS updates.
    'vendor/lib64/libar-pal.so': blob_fixup()
        .call(blob_fixup_elf_u32_symbol, 'pal_log_lvl', 1, need_tmp_dir=False)
        .call(blob_fixup_set_log_level_err_only, 'setPalLogLevel', need_tmp_dir=False),

    'vendor/lib64/libagm.so': blob_fixup()
        .call(blob_fixup_elf_u32_symbol, 'agm_log_lvl', 1, need_tmp_dir=False)
        .call(blob_fixup_set_log_level_err_only, 'setAgmLogLevel', need_tmp_dir=False),

    'vendor/lib64/liblx-osal.so': blob_fixup()
        .call(blob_fixup_elf_u32_symbol, 'ar_log_lvl', 1, need_tmp_dir=False),

    'odm/lib64/libtouchreport_hal.so': blob_fixup()
        .call(blob_fixup_elf_u32_symbol, 'hal_log_level', 1, need_tmp_dir=False),

    'odm/lib64/libtouchreport_alg.so': blob_fixup()
        .call(blob_fixup_elf_u32_symbol, 'alg_log_level', 1, need_tmp_dir=False),

    'odm/lib64/libclient2slpi.notifier.so': blob_fixup()
        .call(
            blob_fixup_silence_log_by_string,
            ['Sensor: notify citsensorservice to trigger cwb'],
            need_tmp_dir=False,
        ),

    'vendor/lib64/libgrallocutils.so': blob_fixup()
        .call(
            blob_fixup_silence_log_by_string,
            ['Explicit UBWC formats such as'],
            need_tmp_dir=False,
        ),

    'odm/bin/hw/vendor.xiaomi.hw.touchfeature-service': blob_fixup()
        .call(
            blob_fixup_silence_log_by_string,
            ['%s: send hand detect result %d'],
            need_tmp_dir=False,
        ),
}  # fmt: skip

module = ExtractUtilsModule(
    'onyx',
    'xiaomi',
    blob_fixups=blob_fixups,
    lib_fixups=lib_fixups,
    namespace_imports=namespace_imports,
    add_firmware_proprietary_file=True,
)

if __name__ == '__main__':
    utils = ExtractUtils.device(module)
    utils.run()
