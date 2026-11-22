#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#


# EXTREME: R8 whole-program optimization for ALL Java modules
FULL_SYSTEM_OPTIMIZE_JAVA := true

# Inherit from those products. Most specific first.
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit_only.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)

# Disable default camera
PRODUCT_NO_CAMERA := true

# Inherit Yasvara standalone common phone configuration.
$(call inherit-product, vendor/yasvara/config/common_phone.mk)

# Inherit from onyx device
$(call inherit-product, device/xiaomi/onyx/device.mk)

# MiuiCamera (replaces Aperture, see PRODUCT_NO_CAMERA above)
$(call inherit-product, device/xiaomi/onyx-miuicamera/device.mk)

PRODUCT_NAME := yasvara_onyx
PRODUCT_DEVICE := onyx
PRODUCT_MANUFACTURER := Xiaomi
PRODUCT_BRAND := POCO
PRODUCT_MODEL := 25053PC47G

PRODUCT_SYSTEM_NAME := onyx_global
PRODUCT_SYSTEM_DEVICE := onyx

# Include all languages
$(call inherit-product, $(SRC_TARGET_DIR)/product/languages_full.mk)

PRODUCT_BUILD_PROP_OVERRIDES += \
    BuildDesc="onyx_global-user 15 AQ3A.250226.002 OS3.0.7.0.WOLMIXM release-keys" \
    BuildFingerprint=POCO/onyx_global/onyx:15/AQ3A.250226.002/OS3.0.7.0.WOLMIXM:user/release-keys \
    DeviceName=$(PRODUCT_SYSTEM_DEVICE) \
    DeviceProduct=$(PRODUCT_SYSTEM_NAME)

PRODUCT_GMS_CLIENTID_BASE := android-xiaomi

PRODUCT_OTA_ENFORCE_VINTF_KERNEL_REQUIREMENTS := false

# Audio Workarounds
PRODUCT_PROPERTY_OVERRIDES += \
    vendor.audio.agm.memlog.enable=false \
    vendor.audio.feature.agm_memlog.enable=false

# Remove AOSP duplicates (replaced by Google Phone, Messages)
# Exclude Google WallpaperPicker (conflicts with AOSP ThemePicker customization)
# In Android 16, use dash prefix to exclude modules from build
PRODUCT_PACKAGES += \
    -Dialer \
    -messaging \
    -WallpaperPickerGoogleRelease \
    -Aperture \
    -Glimpse \
    -Gallery2 \
    -Wellbeing \
    -talkback \
    Messages \
    Photos

# Pentas: game dashboard, per-game GPU/thermal/touch tuning. Event-driven
# (TaskStackListener), so it costs nothing while no game is in front.
PRODUCT_PACKAGES += \
    Pentas \
    Laras

# Alih: translates a game's text in place. Bound only while such a game runs.
PRODUCT_PACKAGES += \
    Alih

# Rekam: screen recorder. Its engine process exists only while recording.
PRODUCT_PACKAGES += \
    Rekam

# SurfaceFlinger performance boost
PRODUCT_PRODUCT_PROPERTIES += \
    ro.surface_flinger.uclamp.min=135

# About phone (design/about-phone): this device's maintainer, and the camera sensors' real
# megapixels per camera id (the HAL reports only the binned arrays, 13 and 5 MP).
PRODUCT_PRODUCT_PROPERTIES += \
    ro.yasvara.maintainer=IRedDragonICY \
    ro.yasvara.maintainer.url=https://github.com/IRedDragonICY \
    ro.yasvara.camera.mp=0:50,1:20

# Optimized DEXopt
PRODUCT_DEX_PREOPT_DEFAULT_COMPILER_FILTER := speed-profile
# system_server = backbone of Android, ALL methods AOT compiled (zero JIT)
PRODUCT_SYSTEM_SERVER_COMPILER_FILTER := speed

PRODUCT_SYSTEM_PROPERTIES += \
    pm.dexopt.post-boot=speed-profile \
    pm.dexopt.install=speed-profile \
    pm.dexopt.install-fast=speed-profile \
    pm.dexopt.bg-dexopt=speed-profile \
    pm.dexopt.first-use=speed-profile \
    pm.dexopt.first-boot=speed-profile \
    pm.dexopt.boot-after-ota=speed-profile \
    pm.dexopt.ab-ota=speed-profile \
    dalvik.vm.dex2oat-filter=speed \
    dalvik.vm.image-dex2oat-filter=speed \
    dalvik.vm.dex2oat-cpu-set=0,1,2,3,4,5,6 \
    dalvik.vm.dex2oat-threads=4 \
    dalvik.vm.boot-dex2oat-threads=8 \
    dalvik.vm.restore-dex2oat-threads=8 \
    dalvik.vm.boot-dex2oat-cpu-set=0,1,2,3,4,5,6,7

# Force speed AOT (100% methods compiled) for performance-critical apps
PRODUCT_DEXPREOPT_SPEED_APPS += \
    Launcher3QuickStep \
    SystemUI \
    Settings \
    Telecom \
    SettingsIntelligence \
    DocumentsUI \
    ThemePicker \
    FaceUnlock \
    Pentas \
    Laras

# Strip unnecessary density resources — POCO F7 is xxhdpi (504 DPI)
# Removes mdpi/hdpi/xhdpi drawables from ALL apps → saves 50-100MB system-wide
# Ship English and Indonesian only: system locales, and every built app's
# resources (aapt2 -c drops other translations; values-in is Indonesian).
PRODUCT_LOCALES := en_US id_ID
PRODUCT_AAPT_CONFIG := normal in
PRODUCT_AAPT_PREF_CONFIG := xxhdpi

# Override dalvik heap for 12GB RAM device (default is 6GB profile)
# Bigger heaps = less GC pauses = smoother Launcher scrolling
PRODUCT_VENDOR_PROPERTIES += \
    dalvik.vm.heapstartsize=24m \
    dalvik.vm.heapgrowthlimit=512m \
    dalvik.vm.heapsize=768m \
    dalvik.vm.heaptargetutilization=0.46 \
    dalvik.vm.heapminfree=8m \
    dalvik.vm.heapmaxfree=48m \
    dalvik.vm.dex2oat-Xms=64m \
    dalvik.vm.dex2oat-Xmx=512m

# EXTREME: Strip ALL debug info from dexpreopt output
# Removes .debug_* sections from .odex files → -30-80MB system-wide
WITH_DEXPREOPT_DEBUG_INFO := false
PRODUCT_OTHER_JAVA_DEBUG_INFO := false
PRODUCT_MINIMIZE_JAVA_DEBUG_INFO := true

# Generate DexMetadata (.dm) files — contains compiler profiles
# Guides dex2oat to prioritize hot methods → better 1st boot app launch
PRODUCT_DEX_PREOPT_GENERATE_DM_FILES := true

# USAP Pool disabled (matches stock HOS 4 and AOSP 17 default): enabling it leaks
# /dev/socket/usap_pool_primary into forked child apps, triggering FinalizerDaemon
# SELinux getopt denials on every app GC.
PRODUCT_SYSTEM_PROPERTIES += \
    dalvik.vm.usap_pool_enabled=false

# ART GC tuning for 12GB RAM — allow bigger heap before GC triggers
PRODUCT_PROPERTY_OVERRIDES += \
    dalvik.vm.foreground-heap-growth-multiplier=2.5

# madvise: Prefetch art files up to 200MB into page cache
# vdex/odex already set to 100MB by AOSP runtime_libart.mk
PRODUCT_SYSTEM_PROPERTIES += \
    dalvik.vm.madvise.artfile.size=209715200

# Disable system tracing daemons & persistent logging — saves CPU + disk writes → battery.
# Place in PRODUCT_PRODUCT_PROPERTIES (/product/etc/build.prop) so system `init` loads them
# AFTER /system/build.prop (overriding base_system.mk's persist.traced.enable=1) without
# hitting vendor_init SELinux property_service denials.
PRODUCT_PRODUCT_PROPERTIES += \
    persist.traced.enable=0 \
    persist.traced_perf.enable=0 \
    logd.logpersistd.enable=false \
    persist.logd.logpersistd=clear

# WiFi PNO scan interval — reduce idle radio wakeups (default ~20s)
PRODUCT_PROPERTY_OVERRIDES += \
    wifi.supplicant_scan_interval=180

# ART lock profiling disabled — removes overhead in userdebug builds
PRODUCT_PROPERTY_OVERRIDES += \
    dalvik.vm.lockprof.threshold=0
