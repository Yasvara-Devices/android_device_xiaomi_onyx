# Device Tree for the POCO F7 (onyx)

```
POCO F7 — Qualcomm Snapdragon 8s Gen 4 (tuna) — 25053PC47G
```

This tree targets Android 16 (LineageOS 23.2 base). It tracks
[xiaomi-onyx-dev/android_device_xiaomi_onyx](https://github.com/xiaomi-onyx-dev/android_device_xiaomi_onyx)
`lineage-23.2` as upstream.

## Repository layout

This device expects these repositories in the source tree:

| Path                | Repository                                                            |
|---------------------|-----------------------------------------------------------------------|
| `device/xiaomi/onyx`   | device tree (this repo)                                            |
| `vendor/xiaomi/onyx`   | [proprietary_vendor_xiaomi_onyx](https://gitlab.com/AdarshGrewal/proprietary_vendor_xiaomi_onyx) (or your fork) |
| `kernel/xiaomi/sm8735` | [android_kernel_xiaomi_sm8735](https://github.com/xiaomi-onyx-dev/android_kernel_xiaomi_sm8735) — 6.6 GKI kernel, built from source |
| `kernel/xiaomi/sm8735-modules` | [android_kernel_xiaomi_sm8735-modules](https://github.com/xiaomi-onyx-dev/android_kernel_xiaomi_sm8735-modules) — QCOM/Xiaomi external modules |
| `kernel/xiaomi/sm8735-devicetrees` | [android_kernel_xiaomi_sm8735-devicetrees](https://github.com/xiaomi-onyx-dev/android_kernel_xiaomi_sm8735-devicetrees) — DT sources, symlinked in as `arch/arm64/boot/dts/vendor` |

### Local manifest snippet

```xml
<?xml version="1.0" encoding="UTF-8"?>
<manifest>
    <remote name="gitlab-poco"
            fetch="https://gitlab.com/poco-f7" />

    <remote name="onyx-dev"
            fetch="https://github.com/xiaomi-onyx-dev" />

    <project path="device/xiaomi/onyx"  name="device_xiaomi_onyx"            remote="gitlab-poco" revision="oss-kernel" />
    <project path="vendor/xiaomi/onyx"  name="proprietary_vendor_xiaomi_onyx" remote="gitlab-poco" revision="oss-kernel" clone-depth="1" />

    <project path="kernel/xiaomi/sm8735"             name="android_kernel_xiaomi_sm8735"             remote="onyx-dev" revision="lineage-23.2" clone-depth="1" />
    <project path="kernel/xiaomi/sm8735-modules"     name="android_kernel_xiaomi_sm8735-modules"     remote="onyx-dev" revision="lineage-23.2" clone-depth="1" />
    <project path="kernel/xiaomi/sm8735-devicetrees" name="android_kernel_xiaomi_sm8735-devicetrees" remote="onyx-dev" revision="lineage-23.2" clone-depth="1" />
</manifest>
```

## Building

Building the kernel needs `libcrypt.so.1` on the host — the Lineage prebuilt perl is
5.26.1 and links against it. On Arch-like distros: `sudo pacman -S libxcrypt-compat`.
Without it the kernel build dies at `arch/arm64/crypto/sha256-core.S` with `Error 127`.

```bash
source build/envsetup.sh
lunch onyx-userdebug
m bacon   # or your ROM's build target
```

## Hardware

| Component        | Details                                    |
|------------------|--------------------------------------------|
| SoC              | Qualcomm SM8735 Snapdragon 8s Gen 4 (tuna) |
| GPU              | Adreno 825                                 |
| Display          | 6.83" 1.5K AMOLED, 120 Hz, 2772x1280       |
| RAM / Storage    | 8/12 GB LPDDR5X, UFS 4.x                   |
| Battery          | 6000 mAh, 90W wired                        |
| Rear cameras     | 50 MP main (OIS) + 8 MP ultra-wide         |
| Front camera     | 20 MP                                      |

## Copyright

```
# SPDX-License-Identifier: Apache-2.0
```

## Kernel

The kernel is built from source (`TARGET_KERNEL_SOURCE := kernel/xiaomi/sm8735`,
config `gki_defconfig + vendor/sun_perf.config + vendor/onyx_perf.config`), together with
the external modules listed in `TARGET_KERNEL_EXT_MODULES`.

Because kernel and modules now come out of a single build, their vermagic always matches.
The `CONFIG_MODVERSIONS` mismatch that used to force a specific prebuilt is gone, and
`binder_gki.ko` no longer exists at all — `CONFIG_ANDROID_BINDER_IPC=y` makes binder
built-in.

`clone-depth="1"` is enough to build. Drop it on `sm8735` before carrying local kernel
patches, since rebasing on upstream needs real history. Prefer adding a new fragment to
`TARGET_KERNEL_CONFIG` over editing `onyx_perf.config`, so upstream syncs stay clean.

### Flashing after a kernel change

The vendor modules live in `vendor_dlkm` and `system_dlkm`, which are dynamic partitions
inside `super` — they are **not** part of `boot`/`vendor_boot`/`dtbo`. Flashing only those
three after a kernel bump leaves stale modules that the new kernel rejects with `-ENOEXEC`,
and the device hangs at the logo with no crash. Flash a full ROM instead.
