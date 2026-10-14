#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
#
# SPDX-FileCopyrightText: 2024 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

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

    # GameSpace's accidental-touch filter is an OSS kernel ABI, not a HAL mode:
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

    # libheif was removed in A17 and no libheif symbol is referenced.
    'system_ext/lib64/libwfdcommonutils.so': blob_fixup()
        .remove_needed('libheif.so'),

    'system_ext/lib64/libwfdmmsrc_system.so': blob_fixup()
        .add_needed('libgui_shim.so'),

    'system_ext/lib64/libwfdnative.so': blob_fixup()
        .add_needed('libbinder_shim.so')
        .add_needed('libinput_shim.so')
        .remove_needed('android.hidl.base@1.0.so'),

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
        .regex_replace(
            r'<minimumLux>4475</minimumLux>',
            r'<minimumLux>2000</minimumLux>',
        )
        .regex_replace(
            r'<ambientLightHorizonLong>1500</ambientLightHorizonLong>',
            r'<ambientLightHorizonLong>2000</ambientLightHorizonLong>',
        )
        .regex_replace(
            r'<ambientLightHorizonShort>1000</ambientLightHorizonShort>',
            r'<ambientLightHorizonShort>500</ambientLightHorizonShort>',
        )
        .regex_replace(
            # Replace stock ramp rates in place (blobs already carry these
            # tags; inserting would duplicate them). Slower tuning from
            # 980c48a/7f94589: gentle fast ramps, lazy slow ramps.
            r'<screenBrightnessRampFastDecrease>[^<]*</screenBrightnessRampFastDecrease>',
            r'<screenBrightnessRampFastDecrease>0.30</screenBrightnessRampFastDecrease>',
        )
        .regex_replace(
            r'<screenBrightnessRampFastIncrease>[^<]*</screenBrightnessRampFastIncrease>',
            r'<screenBrightnessRampFastIncrease>0.30</screenBrightnessRampFastIncrease>',
        )
        .regex_replace(
            r'<screenBrightnessRampSlowDecrease>[^<]*</screenBrightnessRampSlowDecrease>',
            r'<screenBrightnessRampSlowDecrease>0.12</screenBrightnessRampSlowDecrease>',
        )
        .regex_replace(
            r'<screenBrightnessRampSlowIncrease>[^<]*</screenBrightnessRampSlowIncrease>',
            r'<screenBrightnessRampSlowIncrease>0.24</screenBrightnessRampSlowIncrease>',
        )
        .regex_replace(
            r'<screenBrightnessRampIncreaseMaxMillis>[^<]*</screenBrightnessRampIncreaseMaxMillis>',
            r'<screenBrightnessRampIncreaseMaxMillis>2000</screenBrightnessRampIncreaseMaxMillis>',
        )
        .regex_replace(
            r'<screenBrightnessRampDecreaseMaxMillis>[^<]*</screenBrightnessRampDecreaseMaxMillis>',
            r'<screenBrightnessRampDecreaseMaxMillis>5000</screenBrightnessRampDecreaseMaxMillis>',
        ),

    # A17 libbinder reads boot_id through an ifstream (lseek) when ProcessState
    # starts; exit_group keeps a failed init a clean exit instead of SIGSYS.
    'vendor/etc/seccomp_policy/qesdksec.policy': blob_fixup()
        .add_line_if_missing('lseek: 1')
        .add_line_if_missing('exit_group: 1'),

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
    # function epilogue instead. Without this the camera provider aborts on
    # 3rd-party capture, and MiuiCamera loses the provider right after a shot.
    'vendor/lib64/libmicamera_hal_policy.so': blob_fixup()
        .sig_replace('e4 73 00 94 01 74 00 94', 'e473009462ffff17')
        .sig_replace('be 20 00 94 db 20 00 94', 'be20009458ffff17'),

    'vendor/lib64/libqcodec2_core.so': blob_fixup()
        .add_needed('libcodec2_shim.so')
        .replace_needed(
            'android.hardware.graphics.common-V5-ndk.so',
            'android.hardware.graphics.common-V7-ndk.so'
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
