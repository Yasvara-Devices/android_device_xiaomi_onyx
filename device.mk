#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

# Generic ramdisk allow list
$(call inherit-product, $(SRC_TARGET_DIR)/product/generic_ramdisk.mk)

# Project ID Quota
$(call inherit-product, $(SRC_TARGET_DIR)/product/emulated_storage.mk)

# Virtual A/B
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota/launch_with_vendor_ramdisk.mk)

# Dalvik vm configs
$(call inherit-product, frameworks/native/build/phone-xhdpi-6144-dalvik-heap.mk)

# pKVM: AVF (com.android.virt) is left out. On A17 the apex needs the
# android_bootloader_crosvm_aarch64 GBL prebuilt, which the AOSP source drop
# does not ship. Only Microdroid, CompOS and Terminal depend on it.

# Qualcomm
$(call soong_config_set,rfs,mpss_firmware_symlink_target,modem_firmware)
$(call inherit-product, hardware/qcom-caf/common/common.mk)





# A/B
AB_OTA_POSTINSTALL_CONFIG += \
    RUN_POSTINSTALL_system=true \
    POSTINSTALL_PATH_system=system/bin/otapreopt_script \
    FILESYSTEM_TYPE_system=erofs \
    POSTINSTALL_OPTIONAL_system=true

AB_OTA_POSTINSTALL_CONFIG += \
    RUN_POSTINSTALL_vendor=true \
    POSTINSTALL_PATH_vendor=bin/checkpoint_gc \
    FILESYSTEM_TYPE_vendor=erofs \
    POSTINSTALL_OPTIONAL_vendor=true

PRODUCT_PACKAGES += \
    checkpoint_gc \
    otapreopt_script

# AFDO profiles from onyx ETE traces
-include vendor/yasvara/afdo/onyx/afdo_profiles.mk

# API
BOARD_SHIPPING_API_LEVEL := 202404
PRODUCT_SHIPPING_API_LEVEL := 35

PRODUCT_PACKAGES += \
    hwservicemanager \
    android.hidl.allocator@1.0-service \
    android.hidl.memory@1.0-impl

# Audio
PRODUCT_PACKAGES += \
    audio.bluetooth.default \
    audio.r_submix.default \
    audio.usb.default \

PRODUCT_PACKAGES += \
    audioadsprpcd \
    audiohalservice.qti \
    libagm_compress_plugin \
    libagm_mixer_plugin \
    libagm_pcm_plugin \
    libagmipcservice \
    libaudiochargerlistener \
    libbatterylistener \
    libcustomva_intf \
    libfmpal \
    libhfp_pal \
    libhotword_intf \
    libpaleventnotifier \
    libpalipcservice \
    libsndcardparser \
    libsoundtriggerhal.qti \
    libvui_intf \
    qtiaudiohalvendorextn

PRODUCT_PACKAGES += \
    libbundleaidl \
    libdownmixaidl \
    libdynamicsprocessingaidl \
    libloudnessenhanceraidl \
    libqcompostprocbundle \
    libqcomvisualizer \
    libqcomvoiceprocessing \
    libreverbaidl \
    libvisualizeraidl \
    libvolumelistener

PRODUCT_PACKAGES += \
    android.hardware.audio.common-V1-ndk.vendor \
    android.hardware.audio.core-V2-ndk.vendor \
    android.hardware.audio.core.sounddose-V1-ndk.vendor \
    android.hardware.audio.core.sounddose-V2-ndk.vendor \
    android.hardware.audio.effect-V3-ndk.vendor \
    libaudioaidlcommon.vendor \
    libalsautilsv2.vendor \
    libaudioutils_shim \
    libmediautils_vendor.vendor \
    libmemunreachable.vendor

# C2 HIDL compatibility libs (needed by vendor.dolby.media.c2-default-service-dax)
PRODUCT_PACKAGES += \
    android.hardware.media.c2@1.0.vendor \
    android.hardware.media.c2@1.1.vendor \
    android.hardware.media.c2@1.2.vendor \
    libcodec2_hidl@1.0.vendor \
    libcodec2_hidl@1.1.vendor \
    libcodec2_hidl@1.2.vendor \
    libcodec2_soft_common.vendor

# Dolby: the native AIDL DAX3 stack from the stock blobs. The DAP runs on the audio DSP; the
# effect library only carries parameters, and vendor.dolby.dms.service is its parameter
# store. Controlled by NadaService (Laras > Sound).
DOLBY_VENDOR := vendor/xiaomi/onyx/proprietary
PRODUCT_COPY_FILES += \
    $(DOLBY_VENDOR)/vendor/bin/hw/vendor.dolby.media.c2-default-service-dax:$(TARGET_COPY_OUT_VENDOR)/bin/hw/vendor.dolby.media.c2-default-service-dax \
    $(DOLBY_VENDOR)/vendor/lib64/libcodec2_store_dolby.so:$(TARGET_COPY_OUT_VENDOR)/lib64/libcodec2_store_dolby.so \
    $(DOLBY_VENDOR)/vendor/lib64/libdolbydecoderprocessor.so:$(TARGET_COPY_OUT_VENDOR)/lib64/libdolbydecoderprocessor.so \
    $(DOLBY_VENDOR)/vendor/lib64/libdolbyeglcore.so:$(TARGET_COPY_OUT_VENDOR)/lib64/libdolbyeglcore.so \
    $(DOLBY_VENDOR)/vendor/lib64/libdolbyottcameracontrol.so:$(TARGET_COPY_OUT_VENDOR)/lib64/libdolbyottcameracontrol.so \
    $(DOLBY_VENDOR)/vendor/lib64/libqcodec2_dolbydecoderfilter.so:$(TARGET_COPY_OUT_VENDOR)/lib64/libqcodec2_dolbydecoderfilter.so \
    $(DOLBY_VENDOR)/vendor/lib64/libdolbyclstc.so:$(TARGET_COPY_OUT_VENDOR)/lib64/libdolbyclstc.so \
    $(DOLBY_VENDOR)/vendor/lib64/libdeccfg.so:$(TARGET_COPY_OUT_VENDOR)/lib64/libdeccfg.so \
    $(DOLBY_VENDOR)/vendor/lib64/libcodec2_soft_ac4dec.so:$(TARGET_COPY_OUT_VENDOR)/lib64/libcodec2_soft_ac4dec.so \
    $(DOLBY_VENDOR)/vendor/lib64/libcodec2_soft_ddpdec.so:$(TARGET_COPY_OUT_VENDOR)/lib64/libcodec2_soft_ddpdec.so \
    $(DOLBY_VENDOR)/vendor/lib64/libdmshal.so:$(TARGET_COPY_OUT_VENDOR)/lib64/libdmshal.so \
    $(DOLBY_VENDOR)/vendor/lib64/libdapparamstorage.so:$(TARGET_COPY_OUT_VENDOR)/lib64/libdapparamstorage.so \
    $(DOLBY_VENDOR)/vendor/lib64/libdlbdsservice.so:$(TARGET_COPY_OUT_VENDOR)/lib64/libdlbdsservice.so \
    $(DOLBY_VENDOR)/vendor/lib64/libdlbpreg.so:$(TARGET_COPY_OUT_VENDOR)/lib64/libdlbpreg.so \
    $(DOLBY_VENDOR)/vendor/lib64/vendor.dolby.dms-V1-ndk.so:$(TARGET_COPY_OUT_VENDOR)/lib64/vendor.dolby.dms-V1-ndk.so \
    $(DOLBY_VENDOR)/vendor/lib64/vendor.dolby.hardware.dms@2.0.so:$(TARGET_COPY_OUT_VENDOR)/lib64/vendor.dolby.hardware.dms@2.0.so \
    $(DOLBY_VENDOR)/vendor/lib64/soundfx/libmiwndnsprocessingaidl.so:$(TARGET_COPY_OUT_VENDOR)/lib64/soundfx/libmiwndnsprocessingaidl.so \
    $(DOLBY_VENDOR)/vendor/lib64/soundfx/libhwdapaidl.so:$(TARGET_COPY_OUT_VENDOR)/lib64/soundfx/libhwdapaidl.so \
    $(DOLBY_VENDOR)/vendor/lib64/soundfx/libdlbvolaidl.so:$(TARGET_COPY_OUT_VENDOR)/lib64/soundfx/libdlbvolaidl.so \
    $(DOLBY_VENDOR)/vendor/lib64/soundfx/libswspatializeraidl.so:$(TARGET_COPY_OUT_VENDOR)/lib64/soundfx/libswspatializeraidl.so \
    $(DOLBY_VENDOR)/vendor/lib64/soundfx/libswgamedapaidl.so:$(TARGET_COPY_OUT_VENDOR)/lib64/soundfx/libswgamedapaidl.so \
    $(DOLBY_VENDOR)/vendor/etc/init/vendor.dolby.media.c2-default-service-dax.rc:$(TARGET_COPY_OUT_VENDOR)/etc/init/vendor.dolby.media.c2-default-service-dax.rc \
    $(DOLBY_VENDOR)/vendor/etc/media_codecs_dolby_audio.xml:$(TARGET_COPY_OUT_VENDOR)/etc/media_codecs_dolby_audio.xml \
    $(DOLBY_VENDOR)/vendor/etc/dolby/dax-default.xml:$(TARGET_COPY_OUT_VENDOR)/etc/dolby/dax-default.xml \
    $(DOLBY_VENDOR)/vendor/etc/dolby/dax-default-spatializer.xml:$(TARGET_COPY_OUT_VENDOR)/etc/dolby/dax-default-spatializer.xml \
    $(DOLBY_VENDOR)/odm/etc/dolby/dax-default.xml:$(TARGET_COPY_OUT_ODM)/etc/dolby/dax-default.xml \
    $(DOLBY_VENDOR)/odm/etc/dolby/dax-default-spatializer.xml:$(TARGET_COPY_OUT_ODM)/etc/dolby/dax-default-spatializer.xml \
    $(DOLBY_VENDOR)/odm/etc/surfaceflinger/dolby_vision.cfg:$(TARGET_COPY_OUT_ODM)/etc/surfaceflinger/dolby_vision.cfg \
    $(DOLBY_VENDOR)/odm/vendor/etc/dolby_vision.cfg:$(TARGET_COPY_OUT_ODM)/vendor/etc/dolby_vision.cfg \
    $(DOLBY_VENDOR)/odm/bin/hw/dvs-aidl-service:$(TARGET_COPY_OUT_ODM)/bin/hw/dvs-aidl-service \
    $(DOLBY_VENDOR)/odm/etc/init/dvs-aidl-service.rc:$(TARGET_COPY_OUT_ODM)/etc/init/dvs-aidl-service.rc \
    $(DOLBY_VENDOR)/odm/vendor/persist/display/dolby_vision.cfg:$(TARGET_COPY_OUT_ODM)/vendor/persist/display/dolby_vision.cfg

# The Dolby parameter daemon, with the device's own init file. Its VINTF entry is merged
# through DEVICE_MANIFEST_FILE in BoardConfig.mk.
PRODUCT_COPY_FILES += \
    $(DOLBY_VENDOR)/vendor/bin/hw/vendor.dolby.dms.service:$(TARGET_COPY_OUT_VENDOR)/bin/hw/vendor.dolby.dms.service \
    $(LOCAL_PATH)/dolby/dms-service.rc:$(TARGET_COPY_OUT_VENDOR)/etc/init/dms-service.rc

# Dolby Vision - VINTF manifest is installed as a fragment (/odm/etc/vintf/manifest/dvs-aidl-service.xml) via vendor blobs


AUDIO_HAL_DIR := hardware/qcom-caf/sm8750/audio/primary-hal

PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/configs/audio/audio_effects_config.xml:$(TARGET_COPY_OUT_VENDOR)/etc/audio/sku_tuna/audio_effects_config.xml \
    $(LOCAL_PATH)/configs/audio/audio_effects_config.xml:$(TARGET_COPY_OUT_VENDOR)/etc/audio/sku_tuna/audio_effects.xml

PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/configs/audio/audio_module_config_primary.xml:$(TARGET_COPY_OUT_VENDOR)/etc/audio/audio_module_config_primary.xml \
    $(LOCAL_PATH)/configs/audio/audio_policy_configuration.xml:$(TARGET_COPY_OUT_VENDOR)/etc/audio/sku_tuna/audio_policy_configuration.xml

PRODUCT_COPY_FILES += \
    $(AUDIO_HAL_DIR)/../pal/configs/sun/Hapticsconfig.xml:$(TARGET_COPY_OUT_VENDOR)/etc/Hapticsconfig.xml \
    $(AUDIO_HAL_DIR)/configs/sun/quasar_config.xml:$(TARGET_COPY_OUT_VENDOR)/etc/audio/sku_tuna/quasar_config.xml \
    $(AUDIO_HAL_DIR)/configs/sun/vendor_audio_interfaces.xml:$(TARGET_COPY_OUT_VENDOR)/etc/vendor_audio_interfaces.xml \
    $(AUDIO_HAL_DIR)/configs/sun/microphone_characteristics.xml:$(TARGET_COPY_OUT_VENDOR)/etc/microphone_characteristics.xml \

PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/configs/audio/audio_policy_volumes.xml:$(TARGET_COPY_OUT_VENDOR)/etc/audio_policy_volumes.xml \
    frameworks/av/services/audiopolicy/config/default_volume_tables.xml:$(TARGET_COPY_OUT_VENDOR)/etc/default_volume_tables.xml \
    frameworks/av/services/audiopolicy/config/r_submix_audio_policy_configuration.xml:$(TARGET_COPY_OUT_VENDOR)/etc/r_submix_audio_policy_configuration.xml \
    frameworks/av/services/audiopolicy/config/stub_audio_policy_configuration.xml:$(TARGET_COPY_OUT_VENDOR)/etc/stub_audio_policy_configuration.xml

PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.audio.low_latency.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.audio.low_latency.xml \
    frameworks/native/data/etc/android.hardware.audio.pro.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.audio.pro.xml \
    frameworks/native/data/etc/android.software.midi.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.software.midi.xml \
    hardware/interfaces/audio/aidl/default/audio_effects_config.xml:$(TARGET_COPY_OUT_VENDOR)/etc/audio/sku_tuna/audio_effects_config_stub.xml

# Bluetooth
PRODUCT_PACKAGES += \
    android.hardware.bluetooth.audio-impl

PRODUCT_PACKAGES += \
    lib_bt_aptx \
    lib_bt_ble \
    lib_bt_bundle

PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.bluetooth.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.bluetooth.xml \
    frameworks/native/data/etc/android.hardware.bluetooth_le.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.bluetooth_le.xml

# Boot control
PRODUCT_PACKAGES += \
    android.hardware.boot-service.qti \
    android.hardware.boot-service.qti.recovery

# Camera
PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.camera.flash-autofocus.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.camera.flash-autofocus.xml \
    frameworks/native/data/etc/android.hardware.camera.front.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.camera.front.xml \
    frameworks/native/data/etc/android.hardware.camera.full.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.camera.full.xml \
    frameworks/native/data/etc/android.hardware.camera.raw.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.camera.raw.xml

# Characteristics
PRODUCT_CHARACTERISTICS := nosdcard

# DebugFS
PRODUCT_SET_DEBUGFS_RESTRICTIONS := true

# Display - dynamic 60/90/120
$(call soong_config_set,surfaceflinger,frame_rate_category_high,120)
$(call soong_config_set,surfaceflinger,frame_rate_category_min,60)

PRODUCT_PACKAGES += \
    android.hardware.graphics.mapper@4.0-impl-qti-display \
    init.qti.display_boot.rc \
    init.qti.display_boot.sh \
    vendor.qti.hardware.display.allocator-service \
    vendor.qti.hardware.display.demura-service \
    vendor.qti.hardware.display.snapalloc-impl

PRODUCT_PACKAGES += \
    android.hardware.graphics.composer3-V3-ndk.vendor \
    vendor.qti.hardware.display.aiqe-V2-ndk.vendor  \
    vendor.qti.hardware.display.config-V12-ndk.vendor  \
    vendor.qti.hardware.display.composer3-V1-ndk.vendor 

# DRM
PRODUCT_PACKAGES += \
    android.hardware.drm-service.clearkey

# Fastbootd
PRODUCT_PACKAGES += \
    fastbootd

# Fingerprint
$(call soong_config_set,XIAOMI_BIOMETRICS_FINGERPRINT,IMPL_VER,V2)
PRODUCT_PACKAGES += \
    android.hardware.biometrics.fingerprint-service.xiaomi \
    libudfpshandler

PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.fingerprint.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.fingerprint.xml

# Graphics
TARGET_USES_VULKAN = true

PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.vulkan.compute-0.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.vulkan.compute-0.xml \
    frameworks/native/data/etc/android.hardware.vulkan.level-1.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.vulkan.level-1.xml \
    frameworks/native/data/etc/android.hardware.vulkan.version-1_1.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.vulkan.version-1_1.xml \
    frameworks/native/data/etc/android.hardware.vulkan.version-1_3.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.vulkan.version-1_3.xml \
    frameworks/native/data/etc/android.software.vulkan.deqp.level-2023-03-01.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.software.vulkan.deqp.level.xml

PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.opengles.aep.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.opengles.aep.xml \
    frameworks/native/data/etc/android.software.opengles.deqp.level-2023-03-01.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.software.opengles.deqp.level.xml

# framefx: per-game frame generation (Luwes) and color (Kelir), armed from Pentas.
PRODUCT_PACKAGES += \
    libframefx


# GNSS
PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.location.gps.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.location.gps.xml

# Hypsy
PRODUCT_PACKAGES += \
    xiaomi.system.hypsys.common-service-dummy

# MiSys (HypSys) vendor HAL - stages MiuiCamera's watermark layout/assets into
# /data/vendor/camera/watermarks for the MIVI watermark plugin to read.
PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/misys/hypsys_vendor.rc:$(TARGET_COPY_OUT_VENDOR)/etc/init/hypsys_vendor.rc
# Its VINTF fragment goes in BoardConfig.mk - DEVICE_MANIFEST_FILE is a board
# variable and is not picked up from a product makefile.

# Health
PRODUCT_PACKAGES += \
    android.hardware.health-service.qti \
    android.hardware.health-service.qti_recovery

# Offline Charging
# Provides /system/bin/charger binary for offline charging mode (androidboot.mode=charger)
PRODUCT_PACKAGES += \
    charger \
    charger_res_images \
    charger_res_images_vendor

# Enable suspend during charger mode to save power
PRODUCT_SYSTEM_PROPERTIES += \
    ro.charger.enable_suspend=true

# Enable QTI DRM backend for offline charging display
# Qualcomm SDE (qcom,sde-kms) requires atomic modesetting via MinuiBackendDrmQti.
# Without this, libminui uses legacy drmModeSetCrtc which fails on SDE hardware.
$(call soong_config_set_bool,recovery,target_recovery_uses_qti_drm,true)

# IPACM
PRODUCT_PACKAGES += \
    ipacm \
    IPACM_cfg.xml \
    IPACM_Filter_cfg.xml

# Init
PRODUCT_PACKAGES += \
    charger_fw_fstab.qti \
    fstab.qcom

PRODUCT_PACKAGES += \
    ueventd-odm-onyx.rc \
    ueventd-odm.rc \
    ueventd.qcom.rc

PRODUCT_PACKAGES += \
    init.mi_perf.rc \
    init.onyx.rc \
    init.qcom.rc \
    init.qti.kernel.rc \
    init.recovery.qcom.rc \
    init.sensors.onyx.rc \
    init.target.rc \
    mi_thermal_engine

PRODUCT_PACKAGES += \
    init.class_main.sh \
    init.kernel.init_boot-memory.sh \
    init.kernel.post_boot-memory.sh \
    init.kernel.post_boot-tuna.sh \
    init.kernel.post_boot-tuna_default_2_3_2_1.sh \
    init.kernel.post_boot.sh \
    init.qcom.early_boot.sh \
    init.qcom.post_boot.sh \
    init.qcom.sh \
    init.qti.kernel.sh \
    set_charger_poweroff_mode.sh

PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/rootdir/etc/fstab.qcom:$(TARGET_COPY_OUT_VENDOR_RAMDISK)/first_stage_ramdisk/fstab.qcom

# IR
PRODUCT_PACKAGES += \
    android.hardware.ir-service.lineage

PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.consumerir.xml:$(TARGET_COPY_OUT_ODM)/etc/permissions/android.hardware.consumerir.xml

# Keymint
PRODUCT_PACKAGES += \
    android.hardware.authsecret-service.nxp \
    android.hardware.security.keymint3-service.strongbox.nxp \
    android.hardware.weaver-service.nxp

PRODUCT_PACKAGES += \
    android.hardware.hardware_keystore_V3.xml

PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/configs/hal_uuid_map.xml:$(TARGET_COPY_OUT_VENDOR)/etc/hal_uuid_map_onyx.xml

PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.software.device_id_attestation.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.software.device_id_attestation.xml \
    frameworks/native/data/etc/android.hardware.keystore.app_attest_key.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.keystore.app_attest_key.xml

# Lineage Health
PRODUCT_PACKAGES += \
    vendor.lineage.health-service.default

$(call soong_config_set,lineage_health,charging_control_charging_path,/sys/class/xm_power/charger/smart_charge/smart_night)
$(call soong_config_set,lineage_health,charging_control_charging_enabled,0)
$(call soong_config_set,lineage_health,charging_control_charging_disabled,1)
$(call soong_config_set_bool,lineage_health,charging_control_supports_bypass,false)

# Media
PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/configs/media/media_codecs_tuna_v0.xml:$(TARGET_COPY_OUT_VENDOR)/etc/media_codecs_tuna_v0.xml \
    $(LOCAL_PATH)/configs/media/media_codecs_performance_tuna_v0.xml:$(TARGET_COPY_OUT_VENDOR)/etc/media_codecs_performance_tuna_v0.xml \
    $(LOCAL_PATH)/configs/media/video_system_specs.json:$(TARGET_COPY_OUT_VENDOR)/etc/media_tuna_v0/video_system_specs.json \
    $(LOCAL_PATH)/configs/media/media_profiles_tuna_v0.xml:$(TARGET_COPY_OUT_VENDOR)/etc/media_profiles_tuna_v0.xml


PRODUCT_COPY_FILES += \
    $(AUDIO_HAL_DIR)/configs/common/codec2/media_codecs_c2_audio.xml:$(TARGET_COPY_OUT_VENDOR)/etc/media_codecs_c2_audio.xml \
    $(AUDIO_HAL_DIR)/configs/common/codec2/service/1.0/c2audio.vendor.base-arm64.policy:$(TARGET_COPY_OUT_VENDOR)/etc/seccomp_policy/c2audio.vendor.base-arm64.policy \
    $(AUDIO_HAL_DIR)/configs/common/codec2/service/1.0/c2audio.vendor.ext-arm64.policy:$(TARGET_COPY_OUT_VENDOR)/etc/seccomp_policy/c2audio.vendor.ext-arm64.policy

# Memtrack
PRODUCT_PACKAGES += \
    vendor.qti.hardware.memtrack-service

# Micharge
PRODUCT_PACKAGES += \
    vendor.xiaomi.hardware.micharge-service-dummy

# Network
PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.software.ipsec_tunnels.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.software.ipsec_tunnels.xml

# NFC
PRODUCT_PACKAGES += \
    android.hardware.nfc-service.nxp \
    com.android.nfc_extras

PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.nfc.ese.xml:$(TARGET_COPY_OUT_ODM)/etc/permissions/android.hardware.nfc.ese.xml \
    frameworks/native/data/etc/android.hardware.nfc.hce.xml:$(TARGET_COPY_OUT_ODM)/etc/permissions/android.hardware.nfc.hce.xml \
    frameworks/native/data/etc/android.hardware.nfc.hcef.xml:$(TARGET_COPY_OUT_ODM)/etc/permissions/android.hardware.nfc.hcef.xml \
    frameworks/native/data/etc/android.hardware.nfc.uicc.xml:$(TARGET_COPY_OUT_ODM)/etc/permissions/android.hardware.nfc.uicc.xml \
    frameworks/native/data/etc/android.hardware.nfc.xml:$(TARGET_COPY_OUT_ODM)/etc/permissions/android.hardware.nfc.xml \
    frameworks/native/data/etc/android.hardware.se.omapi.ese.xml:$(TARGET_COPY_OUT_ODM)/etc/permissions/android.hardware.se.omapi.ese.xml \
    frameworks/native/data/etc/android.hardware.se.omapi.uicc.xml:$(TARGET_COPY_OUT_ODM)/etc/permissions/android.hardware.se.omapi.uicc.xml \
    frameworks/native/data/etc/com.android.nfc_extras.xml:$(TARGET_COPY_OUT_ODM)/etc/permissions/com.android.nfc_extras.xml \
    frameworks/native/data/etc/com.nxp.mifare.xml:$(TARGET_COPY_OUT_ODM)/etc/permissions/com.nxp.mifare.xml

# Overlays
PRODUCT_PACKAGES += \
    CarrierConfigOverlayOnyx \
    NcmTetheringOverlay \
    SystemUIOverlayOnyx \
    TelephonyOverlayOnyx \
    FrameworkOverlayOnyx \
    FrameworkOverlayOnyxGL \
    LineageSDKOverlayOnyx \
    LineageSettingsOverlayOnyx \
    NfcOverlayOnyx \
    SettingsOverlayOnyx \
    SettingsProviderOverlayOnyx \
    SettingsProviderOverlayOnyxCN \
    SecureElementOverlayOnyx \
    WifiOverlayOnyx \
    WifiOverlayOnyxCN

# Parts
PRODUCT_PACKAGES += \
    XiaomiParts

# Partitions
PRODUCT_USE_DYNAMIC_PARTITIONS := true

PRODUCT_PACKAGES += \
    vendor_bt_firmware_mountpoint \
    vendor_dsp_mountpoint \
    vendor_firmware_mnt_mountpoint \
    vendor_modem_firmware_mountpoint

# Permissions
PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.software.ipsec_tunnel_migration.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.software.ipsec_tunnel_migration.xml


# Power
PRODUCT_PACKAGES += \
    android.hardware.power-service.lineage-libperfmgr \
    libqti-perfd-client

PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/configs/power/powerhint.json:$(TARGET_COPY_OUT_VENDOR)/etc/powerhint.json

$(call soong_config_set,power_libperfmgr,mode_extension_lib,//$(LOCAL_PATH):libpowermode-ext-onyx)

# Properties
PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/properties/odm_CN.prop:$(TARGET_COPY_OUT_ODM)/etc/odm_CN.prop \
    $(LOCAL_PATH)/properties/odm_GL.prop:$(TARGET_COPY_OUT_ODM)/etc/odm_GL.prop \
    $(LOCAL_PATH)/properties/odm_IN.prop:$(TARGET_COPY_OUT_ODM)/etc/odm_IN.prop

# QSPA
PRODUCT_PACKAGES += \
    vendor.qti.qspa-service \
    qspa_vendor.rc

# Reduce system server verbosity.
PRODUCT_SYSTEM_SERVER_DEBUG_INFO := false

# Sensors
PRODUCT_PACKAGES += \
    android.frameworks.sensorservice@1.0.vendor \
    android.hardware.sensors-service.xiaomi-multihal \
    sensors.dynamic_sensor_hal \
    sensors.xiaomi.v2

PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/configs/sensors/hals.conf:$(TARGET_COPY_OUT_ODM)/etc/sensors/hals.conf

PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.sensor.accelerometer.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.sensor.accelerometer.xml \
    frameworks/native/data/etc/android.hardware.sensor.compass.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.sensor.compass.xml \
    frameworks/native/data/etc/android.hardware.sensor.dynamic.head_tracker.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.sensor.dynamic.head_tracker.xml \
    frameworks/native/data/etc/android.hardware.sensor.gyroscope.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.sensor.gyroscope.xml \
    frameworks/native/data/etc/android.hardware.sensor.light.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.sensor.light.xml \
    frameworks/native/data/etc/android.hardware.sensor.proximity.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.sensor.proximity.xml \
    frameworks/native/data/etc/android.hardware.sensor.stepcounter.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.sensor.stepcounter.xml \
    frameworks/native/data/etc/android.hardware.sensor.stepdetector.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.sensor.stepdetector.xml

# Soong namespaces
PRODUCT_SOONG_NAMESPACES += \
    $(LOCAL_PATH) \
    hardware/google/interfaces \
    hardware/google/pixel \
    hardware/lineage/interfaces/power-libperfmgr \
    hardware/qcom-caf/common/libqti-perfd-client \
    hardware/xiaomi

# Telephony
PRODUCT_PACKAGES += \
    extphonelib \
    extphonelib-product \
    extphonelib.xml \
    extphonelib_product.xml \
    ims-ext-common \
    ims_ext_common.xml \
    qti-telephony-hidl-wrapper \
    qti-telephony-hidl-wrapper-prd \
    qti_telephony_hidl_wrapper.xml \
    qti_telephony_hidl_wrapper_prd.xml \
    qti-telephony-utils \
    qti-telephony-utils-prd \
    qti_telephony_utils.xml \
    qti_telephony_utils_prd.xml \
    telephony-ext

PRODUCT_PACKAGES += \
    qcrilNrDb_vendor

PRODUCT_PACKAGES += \
    xiaomi-telephony-stub

PRODUCT_BOOT_JARS += \
    telephony-ext \
    xiaomi-telephony-stub

PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.telephony.cdma.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.telephony.cdma.xml \
    frameworks/native/data/etc/android.hardware.telephony.gsm.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.telephony.gsm.xml \
    frameworks/native/data/etc/android.hardware.telephony.ims.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.telephony.ims.xml \
    frameworks/native/data/etc/android.hardware.telephony.mbms.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.telephony.mbms.xml \
    frameworks/native/data/etc/android.software.sip.voip.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.software.sip.voip.xml

# Thermal
PRODUCT_PACKAGES += \
    android.hardware.thermal-service.qti

# Touchscreen
PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.touchscreen.multitouch.jazzhand.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.touchscreen.multitouch.jazzhand.xml

# Update engine
PRODUCT_PACKAGES += \
    update_engine \
    update_engine_sideload \
    update_verifier

# USB
PRODUCT_PACKAGES += \
    android.hardware.usb-service.qti \
    android.hardware.usb.gadget-service.qti \

PRODUCT_PACKAGES += \
    init.qcom.usb.rc \
    init.qcom.usb.sh \
    usb_compositions.conf

PRODUCT_SOONG_NAMESPACES += \
    vendor/qcom/opensource/usb/etc

PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.usb.accessory.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.usb.accessory.xml \
    frameworks/native/data/etc/android.hardware.usb.host.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.usb.host.xml

# Vendor service manager
PRODUCT_PACKAGES += \
    vndservicemanager

# Verified boot
PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.software.verified_boot.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.software.verified_boot.xml

# Vibrator
PRODUCT_PACKAGES += \
    vendor.qti.hardware.vibrator.service \
    hentak_npu

PRODUCT_COPY_FILES += \
    vendor/qcom/opensource/vibrator/excluded-input-devices.xml:$(TARGET_COPY_OUT_VENDOR)/etc/excluded-input-devices.xml

# WiFi
PRODUCT_PACKAGES += \
    android.hardware.wifi-service \
    hostapd \
    hostapd_cli \
    libwifi-hal-qcom \
    wpa_cli \
    wpa_supplicant \
    wpa_supplicant.conf

PRODUCT_PACKAGES += \
    firmware_wlanmdsp.otaupdate_symlink \
    firmware_wlan_mac.bin_symlink \
    firmware_WCNSS_qcom_cfg.ini_symlink

PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/configs/wifi/p2p_supplicant_overlay.conf:$(TARGET_COPY_OUT_VENDOR)/etc/wifi/p2p_supplicant_overlay.conf \
    $(LOCAL_PATH)/configs/wifi/vendor_cmd.xml:$(TARGET_COPY_OUT_VENDOR)/etc/wifi/vendor_cmd.xml \
    $(LOCAL_PATH)/configs/wifi/WCNSS_qcom_cfg.ini:$(TARGET_COPY_OUT_VENDOR)/etc/wifi/wcn7750/WCNSS_qcom_cfg.ini \
    $(LOCAL_PATH)/configs/wifi/wpa_supplicant_overlay.conf:$(TARGET_COPY_OUT_VENDOR)/etc/wifi/wpa_supplicant_overlay.conf

PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.wifi.direct.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.wifi.direct.xml \
    frameworks/native/data/etc/android.hardware.wifi.passpoint.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.wifi.passpoint.xml \
    frameworks/native/data/etc/android.hardware.wifi.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.wifi.xml \
    frameworks/native/data/etc/android.hardware.wifi.aware.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.wifi.aware.xml

PRODUCT_COPY_FILES += \
    device/xiaomi/onyx/onyx_features.xml:$(TARGET_COPY_OUT_PRODUCT)/etc/device_features/onyx.xml

# Vendor
$(call inherit-product, vendor/xiaomi/onyx/onyx-vendor.mk)

# Laras depth build models (SPEC-0013 §4): onyx has the memory for ToonOut.
$(call inherit-product, vendor/yasvara/prebuilts/depth/depth.mk)
$(call inherit-product, vendor/yasvara/prebuilts/afme/afme.mk)

# Touch IDC (Anti-Ghost Release)
PRODUCT_COPY_FILES += \
    device/xiaomi/onyx/idc/NVTCapacitiveTouchScreen.idc:$(TARGET_COPY_OUT_VENDOR)/usr/idc/NVTCapacitiveTouchScreen.idc

# SmartPA firmware dual-path (kernel firmware_class.path=/odm/firmware/o10u,
# blobs ship at /odm/firmware/ — symlink so direct load doesn't hit -2 fallback)
PRODUCT_PACKAGES += \
    firmware_o10u_aw882xx_acf.bin_symlink \
    firmware_o10u_sipa.bin_symlink \
    firmware_o10u_aw8697_haptic.bin_symlink \
    firmware_o10u_aw8697_rtp_1.bin_symlink


# WFD: libwfdservice NEEDs audio.common.types-V4-cpp, but on A17 libaudioclient
# links V5, so Soong rejects it as a dependency of the blob (aidl multi-version
# check). The blob's shared_libs drop it; install the V4 library here instead.
PRODUCT_PACKAGES += \
    android.media.audio.common.types-V4-cpp

# Layang floating windows (SPEC-0008 §7.1): freeform window management for WM core.
PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.software.freeform_window_management.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.software.freeform_window_management.xml
