/*
 * Copyright (C) 2024 The LineageOS Project
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#define LOG_TAG "UdfpsHandler.onyx"

#include <aidl/android/hardware/biometrics/fingerprint/BnFingerprint.h>
#include <android-base/logging.h>
#include <android-base/unique_fd.h>

#include <poll.h>
#include <sys/ioctl.h>
#include <sys/resource.h>
#include <atomic>
#include <fstream>
#include <mutex>
#include <thread>

#include <display/drm/mi_disp.h>
#include <touch/xiaomi_touch.h>

#include "UdfpsHandler.h"

#define COMMAND_NIT 10
#define PARAM_NIT_FOD 1
#define PARAM_NIT_NONE 0

#define COMMAND_FOD_PRESS_STATUS 1
#define PARAM_FOD_PRESSED 1
#define PARAM_FOD_RELEASED 0

#define DISP_FEATURE_PATH "/dev/mi_display/disp_feature"
#define TOUCH_DEV_PATH "/dev/xiaomi-touch"

using ::aidl::android::hardware::biometrics::fingerprint::AcquiredInfo;

namespace {

static std::shared_ptr<disp_event_resp> parseDispEvent(int fd) {
    disp_event header;
    ssize_t headerSize = read(fd, &header, sizeof(header));
    if (headerSize < sizeof(header)) {
        LOG(ERROR) << "unexpected display event header size: " << headerSize;
        return nullptr;
    }

    std::shared_ptr<disp_event_resp> response(static_cast<disp_event_resp*>(malloc(header.length)),
                                              free);
    if (!response) {
        LOG(ERROR) << "failed to allocate memory for display event response";
        return nullptr;
    }
    response->base = header;

    int dataLength = response->base.length - sizeof(response->base);
    if (dataLength < 0) {
        LOG(ERROR) << "invalid data length: " << response->base.length;
        return nullptr;
    }

    ssize_t dataSize = read(fd, &response->data, dataLength);
    if (dataSize < dataLength) {
        LOG(ERROR) << "unexpected display event data size: " << dataSize;
        return nullptr;
    }

    return response;
}

struct disp_base displayBasePrimary = {
        .flag = 0,
        .disp_id = MI_DISP_PRIMARY,
};

common_data_t touchDataPrimary = {
        .touch_id = MI_DISP_PRIMARY,
        .cmd = SET_CUR_VALUE,
        .mode = 0,
        .data_len = 1,
        .data_buf = {},
};

}  // anonymous namespace

class XiaomiOnyxUdfpsHandler : public UdfpsHandler {
  public:
    void init(fingerprint_device_t* device) {
        mDevice = device;
        touch_fd_ = android::base::unique_fd(open(TOUCH_DEV_PATH, O_RDWR));
        disp_fd_ = android::base::unique_fd(open(DISP_FEATURE_PATH, O_RDWR));

        ioctl(touch_fd_.get(), TOUCH_IOC_SELECT_TOUCH_ID, MI_DISP_PRIMARY);

        // Thread to listen for fod ui changes
        std::thread([this]() {
            setpriority(PRIO_PROCESS, 0, -20);
            android::base::unique_fd fd(open(DISP_FEATURE_PATH, O_RDWR));
            if (fd < 0) {
                LOG(ERROR) << "failed to open " << DISP_FEATURE_PATH << " , err: " << fd;
                return;
            }

            // FOD for the LHBM ui-ready handshake, POWER to know when the panel is in doze.
            for (__u32 type : {MI_DISP_EVENT_FOD, MI_DISP_EVENT_POWER}) {
                struct disp_event_req displayEventRequest = {
                        .base = displayBasePrimary,
                        .type = type,
                };
                if (ioctl(fd.get(), MI_DISP_IOCTL_REGISTER_EVENT, &displayEventRequest) < 0) {
                    LOG(ERROR) << "failed to register display event " << type;
                    return;
                }
            }

            struct pollfd dispEventPoll = {
                    .fd = fd.get(),
                    .events = POLLIN,
                    .revents = 0,
            };

            while (true) {
                int pollResult = poll(&dispEventPoll, 1, -1);
                if (pollResult < 0) {
                    LOG(ERROR) << "failed to poll " << DISP_FEATURE_PATH << " , err: " << pollResult;
                    continue;
                }

                if (!(dispEventPoll.revents & POLLIN)) {
                    continue;
                }

                std::shared_ptr<disp_event_resp> response = parseDispEvent(fd.get());
                if (!response) {
                    continue;
                }

                if (response->base.type == MI_DISP_EVENT_POWER) {
                    onPowerMode(response->data[0]);
                    continue;
                }
                if (response->base.type != MI_DISP_EVENT_FOD) {
                    LOG(ERROR) << "unexpected display event: " << response->base.type;
                    continue;
                }

                int value = response->data[0];
                LOG(DEBUG) << "received data: " << std::bitset<8>(value);

                // In doze the kernel first reports it is waiting for a refresh-rate switch, with
                // the ready bit clear. That is not local HBM going away: forwarding it makes the
                // sensor abort the capture before the light ever comes up.
                if (value & LOCAL_HBM_NEED_UPDATE_TO_FOD_FPS) continue;
                bool localHbmUiReady = value & LOCAL_HBM_UI_READY;
                if (localHbmUiReady == mUiReady.exchange(localHbmUiReady)) continue;

                mDevice->extCmd(mDevice, COMMAND_NIT,
                                localHbmUiReady ? PARAM_NIT_FOD : PARAM_NIT_NONE);
            }
        }).detach();
    }

    void onFingerDown(uint32_t /*x*/, uint32_t /*y*/, float /*minor*/, float /*major*/) {
        if (mAuthSuccess) return;
        LOG(INFO) << __func__;
        mFingerDown = true;
        mDevice->extCmd(mDevice, COMMAND_FOD_PRESS_STATUS, PARAM_FOD_PRESSED);

        common_data_t data = touchDataPrimary;
        data.mode = THP_FOD_DOWNUP_CTL;
        data.data_buf[0] = 1;
        ioctl(touch_fd_.get(), TOUCH_IOC_COMMON_DATA, &data);

        std::lock_guard<std::mutex> lock(mPanelLock);
        if (panelDark()) {
            // A screen-off press reaches us before the panel is up; light it once it is.
            mLhbmPending = true;
            return;
        }
        requestLhbmLocked();
    }

    void onFingerUp() {
        LOG(INFO) << __func__;
        mFingerDown = false;
        mDevice->extCmd(mDevice, COMMAND_FOD_PRESS_STATUS, PARAM_FOD_RELEASED);

        common_data_t data = touchDataPrimary;
        data.mode = THP_FOD_DOWNUP_CTL;
        data.data_buf[0] = 0;
        ioctl(touch_fd_.get(), TOUCH_IOC_COMMON_DATA, &data);

        // Disable HBM
        struct disp_local_hbm_req displayLhbmRequest = {
                .base = displayBasePrimary,
                .local_hbm_value = LHBM_TARGET_BRIGHTNESS_OFF_FINGER_UP,
        };
        ioctl(disp_fd_.get(), MI_DISP_IOCTL_SET_LOCAL_HBM, &displayLhbmRequest);

        std::lock_guard<std::mutex> lock(mPanelLock);
        mLhbmPending = false;
        if (mDozeRaised) {
            setDozeBrightness(DOZE_TO_NORMAL);
            mDozeRaised = false;
        }
    }

    void onAcquired(int32_t result, int32_t vendorCode) {
        LOG(INFO) << __func__ << " result: " << result << " vendorCode: " << vendorCode;
        switch (static_cast<AcquiredInfo>(result)) {
            case AcquiredInfo::GOOD:
            case AcquiredInfo::PARTIAL:
            case AcquiredInfo::INSUFFICIENT:
            case AcquiredInfo::SENSOR_DIRTY:
            case AcquiredInfo::TOO_SLOW:
            case AcquiredInfo::TOO_FAST:
            case AcquiredInfo::TOO_DARK:
            case AcquiredInfo::TOO_BRIGHT:
            case AcquiredInfo::IMMOBILE:
            case AcquiredInfo::LIFT_TOO_SOON:
                onFingerUp();
                break;
            default:
                break;
        }
    }

    void cancel() {
        LOG(INFO) << __func__;
        onFingerUp();
    }

    void onAuthenticationSucceeded() {
        mAuthSuccess = true;
        onFingerUp();
        std::thread([this]() {
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
            mAuthSuccess = false;
        }).detach();
    }

    void onAuthenticationFailed() { onFingerUp(); }

  private:
    bool panelDark() const {
        return mPowerMode != MI_DISP_POWER_ON && mPowerMode != MI_DISP_POWER_LP1 &&
               mPowerMode != MI_DISP_POWER_LP2;
    }

    void setDozeBrightness(__u32 value) {
        struct disp_doze_brightness_req req = {
                .base = displayBasePrimary,
                .doze_brightness = value,
        };
        if (ioctl(disp_fd_.get(), MI_DISP_IOCTL_SET_DOZE_BRIGHTNESS, &req) < 0)
            PLOG(ERROR) << "set doze brightness " << value;
    }

    // In doze the kernel picks the HLPM local-HBM command only once the panel is in an AOD
    // brightness state; at doze brightness 0 it sends the normal one, which the panel ignores
    // there, and capture runs dark. Must precede the LHBM request: it is skipped once FOD HBM is
    // on.
    void requestLhbmLocked() {
        if ((mPowerMode == MI_DISP_POWER_LP1 || mPowerMode == MI_DISP_POWER_LP2) &&
            !mDozeRaised) {
            setDozeBrightness(DOZE_BRIGHTNESS_HBM);
            mDozeRaised = true;
        }
        struct disp_local_hbm_req displayLhbmRequest = {
                .base = displayBasePrimary,
                .local_hbm_value = LHBM_TARGET_BRIGHTNESS_WHITE_1000NIT,
        };
        ioctl(disp_fd_.get(), MI_DISP_IOCTL_SET_LOCAL_HBM, &displayLhbmRequest);
    }

    void onPowerMode(int mode) {
        std::lock_guard<std::mutex> lock(mPanelLock);
        mPowerMode = mode;
        // The kernel resets the AOD brightness state on any ON/OFF transition.
        if (mode != MI_DISP_POWER_LP1 && mode != MI_DISP_POWER_LP2) mDozeRaised = false;
        if (mLhbmPending && !panelDark()) {
            mLhbmPending = false;
            if (mFingerDown) requestLhbmLocked();
        }
    }

    fingerprint_device_t* mDevice;
    android::base::unique_fd touch_fd_;
    android::base::unique_fd disp_fd_;
    // Touched from binder threads and from the mAuthSuccess reset thread.
    std::atomic<bool> mAuthSuccess = false;
    std::atomic<bool> mFingerDown = false;
    std::atomic<bool> mUiReady = false;

    std::mutex mPanelLock;
    int mPowerMode = MI_DISP_POWER_ON;  // until the first event; the HAL starts with the screen on
    bool mLhbmPending = false;
    bool mDozeRaised = false;
};

static UdfpsHandler* create() {
    return new XiaomiOnyxUdfpsHandler();
}

static void destroy(UdfpsHandler* handler) {
    delete handler;
}

extern "C" UdfpsHandlerFactory UDFPS_HANDLER_FACTORY = {
        .create = create,
        .destroy = destroy,
};
