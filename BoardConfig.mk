#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

DEVICE_PATH := device/xiaomi/onyx

BUILD_BROKEN_DUP_RULES := true
BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES := true

# A/B
AB_OTA_UPDATER := true
# Full-image REPLACE ops as zstd (level 22) instead of xz/bzip2: about the same size, but
# recovery's update_engine decompresses on one thread and zstd decodes ~10x faster.
BOARD_OTA_EXTRA_ARGS := --enable_replace_zstd=true

# 8 Scudo TSDs instead of 2: less allocator lock contention in threaded apps.
MALLOC_SCUDO_TSDS_MAX := true

AB_OTA_PARTITIONS := \
    boot \
    dtbo \
    init_boot \
    odm \
    product \
    recovery \
    system \
    system_dlkm \
    system_ext \
    vbmeta \
    vbmeta_system \
    vendor \
    vendor_boot \
    vendor_dlkm

# Architecture
# onyx is 1x Cortex-X4 (MIDR part 0xd82) + 7x Cortex-A720 (0xd81), implementer
# 0x41 (ARM) -- Armv9.2, and emphatically not Oryon.
#
# TARGET_CPU_VARIANT feeds two consumers: -mcpu for native code, and
# --instruction-set-variant for dex2oat. "generic" was costing us on both. ART
# lists "generic" under arm64_variants_with_a53_835769_bug, so every AOT-compiled
# method carried Cortex-A53 errata workarounds and none of LSE / FP16 / dotprod,
# despite atomics+fphp+asimddp all being present in HWCAP.
#
# -march wins over -mcpu for ISA selection (-mcpu only supplies tuning when both
# are given), so the arch variant has to be raised as well or none of the Armv9
# gains materialise. armv9-a carries +nosve, which is required: the kernel does
# not advertise SVE in HWCAP here, so emitting it would trap.
#
# Yasvara build/soong + art carry the cortex-a720 variant and an armv9-a with
# +nosve.
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv9-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_VARIANT := cortex-a720
TARGET_CPU_VARIANT_RUNTIME := cortex-a720

# Control Flow Integrity off, for performance.
#
# The obvious half is dropping the cross-DSO indirect-call checks (every such
# call otherwise goes through __cfi_slowpath). The larger half is less obvious:
# Soong links every CFI-enabled module with -Wl,-plugin-opt,O1 (see cfiLdflags
# in build/soong/cc/sanitize.go), which capped LTO codegen at O1 for 1120
# shared libraries here. Turning CFI off moves those onto the normal LTO path,
# so they pick up -flto=full and --lto-O3 like everything else.
#
# This is invisible to userspace: no API reports whether a native library was
# built with CFI, and Play Integrity does not sample it. Banking-app standing
# depends on SELinux enforcing, ro.debuggable=0, verified boot green and an
# intact vbmeta -- none of which this touches. Verified against the two
# installed on this device (Bank Jago, GoPay).
#
# NOTE: do not "also" disable branchprot to save more. arm64ArchFeatureCflags
# pairs -mbranch-protection=standard with -fno-stack-protector, so dropping it
# removes PAC (paciasp/autiasp: a couple of cycles, no memory traffic) and
# reinstates the stack-protector canary (TLS load, spill, reload, compare) on
# 33679 modules. That trade loses.
ENABLE_CFI := false

# Audio
AUDIO_FEATURE_ENABLED_DLKM := true
AUDIO_FEATURE_ENABLED_EXTENDED_COMPRESS_FORMAT := true
AUDIO_FEATURE_ENABLED_GKI := true
AUDIO_FEATURE_ENABLED_INSTANCE_ID := true
AUDIO_FEATURE_ENABLED_MCS := true
AUDIO_FEATURE_ENABLED_SVA_MULTI_STAGE := true
BOARD_SUPPORTS_OPENSOURCE_STHAL := true
BOARD_SUPPORTS_SOUND_TRIGGER := true
BOARD_USES_ALSA_AUDIO := true
TARGET_PROVIDES_AUDIO_HAL := true
TARGET_PROVIDES_LIBAGM := true
TARGET_PROVIDES_LIBAR_PAL := true

# Bluetooth
BOARD_BLUETOOTH_BDROID_BUILDCFG_INCLUDE_DIR := $(DEVICE_PATH)/bluetooth/include

# Bootloader
TARGET_BOOTLOADER_BOARD_NAME := sun

# Display
TARGET_SCREEN_DENSITY := 504

# Filesystem
TARGET_FS_CONFIG_GEN := $(DEVICE_PATH)/configs/config.fs

# HIDL
DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE += \
    $(DEVICE_PATH)/configs/hidl/compatibility_matrix.device.xml \
    hardware/qcom-caf/common/vendor_framework_compatibility_matrix.xml \

DEVICE_MATRIX_FILE := hardware/qcom-caf/common/compatibility_matrix_aidl.xml
DEVICE_MANIFEST_FILE += \
    $(DEVICE_PATH)/configs/hidl/manifest.xml \
    hardware/qcom-caf/sm8750/audio/primary-hal/configs/sun/manifest_audio_qti_services.xml \
    $(DEVICE_PATH)/misys/vendor.xiaomi.hardware.misys.common.xml \
    $(DEVICE_PATH)/misys/manifest_blackbox.xml

# HWUI
HWUI_COMPILE_FOR_PERF := true

# Kernel
BOARD_INCLUDE_DTB_IN_BOOTIMG := true
BOARD_RAMDISK_USE_LZ4 := true
TARGET_NEEDS_DTBOIMAGE := true

BOARD_KERNEL_BASE := 0x00000000
BOARD_KERNEL_PAGESIZE := 4096
BOARD_KERNEL_IMAGE_NAME := Image

BOARD_BOOT_HEADER_VERSION := 4
BOARD_MKBOOTIMG_ARGS := --header_version $(BOARD_BOOT_HEADER_VERSION)

BOARD_INIT_BOOT_HEADER_VERSION := 4
BOARD_MKBOOTIMG_INIT_ARGS += --header_version $(BOARD_INIT_BOOT_HEADER_VERSION)

BOARD_USES_QCOM_MERGE_DTBS_SCRIPT := true

TARGET_KERNEL_ADDITIONAL_FLAGS := TARGET_PRODUCT=$(PRODUCT_DEVICE)
TARGET_KERNEL_SOURCE := kernel/xiaomi/sm8735
# Clang 21, the toolchain this kernel tree is validated with. clang-stable
# (r596125, Clang 22) ships a libclang that bindgen cannot load.
TARGET_KERNEL_CLANG_VERSION := r563880c
TARGET_KERNEL_CONFIG := \
    gki_defconfig \
    vendor/sun_perf.config \
    vendor/onyx_perf.config \
    $(TARGET_KERNEL_CONFIG_EXTRA)

# Appended to the bootargs that tuna.dtsi already supplies. Kept here rather
# than in the devicetree so the QCOM-owned dtsi stays unmodified and these can
# be reverted by rebuilding boot.img alone.
#
# init_on_alloc=0 - gki_defconfig sets CONFIG_INIT_ON_ALLOC_DEFAULT_ON=y, which
#   zeroes every page allocation. It is gated by a static key that this early
#   param flips (mm/mm_init.c:2703), so no kernel rebuild is needed to A/B it.
#   This IS a real hardening regression - it is what stops freshly allocated
#   memory from leaking previous contents - and is accepted deliberately here
#   for a personal device.
#
# kfence.sample_interval=0 - KFENCE is a sampling use-after-free/OOB detector.
#   CONFIG_KFENCE_STATIC_KEYS is not set in this tree, so its per-allocation
#   cost is a counter check rather than a patched branch; 0 makes kfence_init()
#   bail out entirely (mm/kfence/core.c:846). Expected gain is small - this is
#   here to be measured, not because it is known to matter.
BOARD_KERNEL_CMDLINE := \
    video=vfb:640x400,bpp=32,memsize=3072000 \
    sysctl.kernel.firmware_config.force_sysfs_fallback=1 \
    init_on_alloc=0 \
    kfence.sample_interval=0 \
    kasan=off \
    kernel.panic_on_rcu_stall=0 \
    page_alloc.shuffle=0 \
    randomize_kstack_offset=0 \
    mitigations=off \
    nowatchdog \
    loglevel=0 \
    swinfo.fingerprint=$(YASVARA_VERSION) \
    mtdoops.fingerprint=$(YASVARA_VERSION) \
    bootmonitor.fingerprint=$(YASVARA_VERSION)


BOARD_BOOTCONFIG := \
    androidboot.hardware=qcom \
    androidboot.memcg=1 \
    androidboot.serialconsole=0 \
    androidboot.usbcontroller=a600000.dwc3 \
    androidboot.load_modules_parallel=true \
    androidboot.hypervisor.protected_vm.supported=true \
    androidboot.vendor.qspa=true

# Kernel modules
first_stage_modules := $(strip $(shell sed 's/#.*$$//;/^$$/d' $(TARGET_KERNEL_SOURCE)/modules.list.msm.sun $(DEVICE_PATH)/modules/modules.list.first_stage))
second_stage_modules := $(strip $(shell sed 's/#.*$$//;/^$$/d' $(DEVICE_PATH)/modules/modules.list.second_stage))
vendor_dlkm_modules := $(strip $(shell sed 's/#.*$$//;/^$$/d' $(DEVICE_PATH)/modules/modules.list.vendor_dlkm))

bzl-modules = $(shell sed -n '$(foreach b,$(1),/^$(b)/,/^]/p;)' $(TARGET_KERNEL_SOURCE)/modules.bzl | sed -n 's,^[[:space:]]*".*/\([^"]*\)".*,\1,p')
gki_modules := $(strip $(call bzl-modules,_COMMON_GKI _ARM64_GKI))

BOARD_SYSTEM_KERNEL_MODULES_LOAD := $(gki_modules)
BOARD_VENDOR_KERNEL_MODULES_BLOCKLIST_FILE := $(TARGET_KERNEL_SOURCE)/modules.vendor_blocklist.msm.sun
BOARD_VENDOR_KERNEL_MODULES_LOAD := $(second_stage_modules) $(vendor_dlkm_modules)
BOARD_VENDOR_RAMDISK_KERNEL_MODULES_BLOCKLIST_FILE := $(BOARD_VENDOR_KERNEL_MODULES_BLOCKLIST_FILE)
BOARD_VENDOR_RAMDISK_KERNEL_MODULES_LOAD := $(first_stage_modules)
BOARD_VENDOR_RAMDISK_RECOVERY_KERNEL_MODULES_LOAD := $(first_stage_modules) $(second_stage_modules)

BOOT_KERNEL_MODULES := $(first_stage_modules) $(second_stage_modules)
SYSTEM_KERNEL_MODULES := $(gki_modules)

TARGET_KERNEL_EXT_MODULE_ROOT := kernel/xiaomi/sm8735-modules
TARGET_KERNEL_EXT_MODULES := \
    qcom/opensource/mmrm-driver \
    qcom/opensource/mm-drivers/hw_fence \
    qcom/opensource/mm-drivers/msm_ext_display \
    qcom/opensource/mm-drivers/sync_fence \
    qcom/opensource/audio-kernel \
    qcom/opensource/securemsm-kernel \
    qcom/opensource/synx-kernel \
    qcom/opensource/camera-kernel \
    qcom/opensource/data-kernel/drivers/smem-mailbox \
    qcom/opensource/datarmnet-ext/mem \
    qcom/opensource/dataipa/drivers/platform/msm \
    qcom/opensource/datarmnet/core \
    qcom/opensource/datarmnet-ext/aps \
    qcom/opensource/datarmnet-ext/offload \
    qcom/opensource/datarmnet-ext/perf \
    qcom/opensource/datarmnet-ext/perf_tether \
    qcom/opensource/datarmnet-ext/sch \
    qcom/opensource/datarmnet-ext/shs \
    qcom/opensource/datarmnet-ext/wlan \
    qcom/opensource/display-drivers/msm \
    qcom/opensource/dsp-kernel \
    qcom/opensource/eva-kernel \
    qcom/opensource/graphics-kernel \
    qcom/opensource/spu-kernel \
    qcom/opensource/touch-drivers \
    qcom/opensource/video-driver \
    qcom/opensource/wlan/platform \
    qcom/opensource/wlan/qcacld-3.0 \
    qcom/opensource/bt-kernel \
    nxp/opensource/driver

# Partitions
BOARD_BOOTIMAGE_PARTITION_SIZE := 100663296
BOARD_DTBOIMG_PARTITION_SIZE := 25165824
BOARD_INIT_BOOT_IMAGE_PARTITION_SIZE := 8388608
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 104857600
BOARD_SUPER_PARTITION_SIZE := 11811160064
BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE := 100663296

BOARD_FLASH_BLOCK_SIZE := 131072 # (BOARD_KERNEL_PAGESIZE * 64)

BOARD_USES_METADATA_PARTITION := true

BOARD_QTI_DYNAMIC_PARTITIONS_PARTITION_LIST := odm product system system_dlkm system_ext vendor vendor_dlkm
BOARD_QTI_DYNAMIC_PARTITIONS_SIZE := 11806965760 # (BOARD_SUPER_PARTITION_SIZE - 4 MiB)
BOARD_SUPER_PARTITION_GROUPS := qti_dynamic_partitions

BOARD_ODMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_PRODUCTIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_SYSTEM_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_SYSTEM_EXTIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_VENDOR_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs

# EROFS compression: LZ4HC level 12 (MAXIMUM compression, same decompress speed)
BOARD_SYSTEMIMAGE_EROFS_COMPRESSOR := lz4hc,12
BOARD_SYSTEMIMAGE_EROFS_PCLUSTER_SIZE := 262144
BOARD_SYSTEM_EXTIMAGE_EROFS_COMPRESSOR := lz4hc,12
BOARD_SYSTEM_EXTIMAGE_EROFS_PCLUSTER_SIZE := 262144
BOARD_PRODUCTIMAGE_EROFS_COMPRESSOR := lz4hc,12
BOARD_PRODUCTIMAGE_EROFS_PCLUSTER_SIZE := 262144

TARGET_COPY_OUT_ODM := odm
TARGET_COPY_OUT_PRODUCT := product
TARGET_COPY_OUT_SYSTEM := system
TARGET_COPY_OUT_SYSTEM_DLKM := system_dlkm
TARGET_COPY_OUT_SYSTEM_EXT := system_ext
TARGET_COPY_OUT_VENDOR := vendor
TARGET_COPY_OUT_VENDOR_DLKM := vendor_dlkm


# Platform
BOARD_USES_QCOM_HARDWARE := true
TARGET_BOARD_PLATFORM := sun

BOARD_ROOT_EXTRA_SYMLINKS := \
    /vendor/firmware_mnt:/firmware \
    /vendor/bt_firmware:/bt_firmware \
    /vendor/dsp:/dsp

# Properties
TARGET_ODM_PROP += $(DEVICE_PATH)/properties/odm.prop
TARGET_PRODUCT_PROP += $(DEVICE_PATH)/properties/product.prop
TARGET_SYSTEM_PROP += $(DEVICE_PATH)/properties/system.prop
TARGET_SYSTEM_EXT_PROP += $(DEVICE_PATH)/properties/system_ext.prop
TARGET_VENDOR_PROP += $(DEVICE_PATH)/properties/vendor.prop

# Recovery
BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE := true
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/rootdir/etc/fstab.qcom
TARGET_RECOVERY_PIXEL_FORMAT := RGBX_8888
TARGET_USERIMAGES_USE_F2FS := true

# RIL
ENABLE_VENDOR_RIL_SERVICE := true

# Sepolicy
include vendor/yasvara/sepolicy/common/sepolicy.mk
include vendor/yasvara/sepolicy/libperfmgr/sepolicy.mk
include device/qcom/sepolicy_vndr/SEPolicy.mk
include packages/apps/Pentas/sepolicy/sepolicy.mk
SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS += $(DEVICE_PATH)/sepolicy/private
BOARD_VENDOR_SEPOLICY_DIRS += $(DEVICE_PATH)/sepolicy/vendor
SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS += $(DEVICE_PATH)/sepolicy/public

# Vendor security patch
VENDOR_SECURITY_PATCH := 2026-02-01

# Verified Boot
BOARD_AVB_ENABLE := true
BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS += --flags 3
BOARD_AVB_ALGORITHM := SHA256_RSA2048
BOARD_AVB_KEY_PATH := external/avb/test/data/testkey_rsa2048.pem
BOARD_MOVE_GSI_AVB_KEYS_TO_VENDOR_BOOT := true

BOARD_AVB_BOOT_KEY_PATH := external/avb/test/data/testkey_rsa2048.pem
BOARD_AVB_BOOT_ALGORITHM := SHA256_RSA2048
BOARD_AVB_BOOT_ROLLBACK_INDEX := $(PLATFORM_SECURITY_PATCH_TIMESTAMP)
BOARD_AVB_BOOT_ROLLBACK_INDEX_LOCATION := 3

BOARD_AVB_RECOVERY_KEY_PATH := external/avb/test/data/testkey_rsa2048.pem
BOARD_AVB_RECOVERY_ALGORITHM := SHA256_RSA2048
BOARD_AVB_RECOVERY_ROLLBACK_INDEX := $(PLATFORM_SECURITY_PATCH_TIMESTAMP)
BOARD_AVB_RECOVERY_ROLLBACK_INDEX_LOCATION := 1

BOARD_AVB_VBMETA_SYSTEM := system system_dlkm system_ext product
BOARD_AVB_VBMETA_SYSTEM_KEY_PATH := external/avb/test/data/testkey_rsa2048.pem
BOARD_AVB_VBMETA_SYSTEM_ALGORITHM := SHA256_RSA2048
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX := $(PLATFORM_SECURITY_PATCH_TIMESTAMP)
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX_LOCATION := 2

BOARD_AVB_VENDOR_DLKM_ADD_HASHTREE_FOOTER_ARGS += --hash_algorithm sha256
BOARD_AVB_VENDOR_ADD_HASHTREE_FOOTER_ARGS += --hash_algorithm sha256
BOARD_AVB_SYSTEM_DLKM_ADD_HASHTREE_FOOTER_ARGS += --hash_algorithm sha256

# WiFi
BOARD_WLAN_DEVICE := qcwcn
BOARD_HOSTAPD_DRIVER := NL80211
BOARD_HOSTAPD_PRIVATE_LIB := lib_driver_cmd_$(BOARD_WLAN_DEVICE)
BOARD_WPA_SUPPLICANT_DRIVER := NL80211
BOARD_WPA_SUPPLICANT_PRIVATE_LIB := lib_driver_cmd_$(BOARD_WLAN_DEVICE)
# (1 STA + 1 AP) or (1 STA + 1 of (P2P or NAN)) or (2 AP) or (2 STA)
WIFI_HAL_INTERFACE_COMBINATIONS := {{{STA}, 1}, {{AP}, 1}}, {{{STA}, 1}, {{P2P, NAN}, 1}}, {{{AP}, 2}}, {{{STA}, 2}}
WIFI_DRIVER_DEFAULT := qca_cld3
WIFI_DRIVER_STATE_CTRL_PARAM := "/dev/wlan"
WIFI_DRIVER_STATE_OFF := "OFF"
WIFI_DRIVER_STATE_ON := "ON"
WIFI_FEATURE_HOSTAPD_11AX := true
WIFI_HIDL_UNIFIED_SUPPLICANT_SERVICE_RC_ENTRY := true
WPA_SUPPLICANT_VERSION := VER_0_8_X

# Vendor
include vendor/xiaomi/onyx/BoardConfigVendor.mk

BUILD_BROKEN_VINTF_COMPATIBILITY := true
DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE += device/xiaomi/onyx/framework_compat_matrix.xml
# MiuiCamera — pulls in system.prop and the vendor sepolicy dir, and includes
# vendor/xiaomi/onyx-miuicamera/BoardConfigVendor.mk itself.
include device/xiaomi/onyx-miuicamera/BoardConfig.mk
