/*
 * SPDX-FileCopyrightText: The LineageOS Project
 * SPDX-License-Identifier: Apache-2.0
 */

package com.xiaomi.settings.touch

import android.app.Service
import android.content.Context
import android.content.Intent
import android.database.ContentObserver
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.UserHandle
import android.provider.Settings
import android.util.Log
import java.io.File
import java.io.IOException

/**
 * Arms single tap to wake on the touch driver.
 *
 * Double tap to wake needs nothing here - PowerManagerService arms it through the power HAL. There
 * is no equivalent AOSP path for single tap, so this service is what turns the setting into an
 * armed panel gesture.
 *
 * The tap event itself never comes back through here: the panel reports KEY_WAKEUP and
 * PowerManagerService wakes the device straight off the input path. This service only decides
 * whether the panel should be scanning at all.
 *
 * The node is only written while the screen is on. nvt_set_gesture_mode() defers any gesture change
 * made against a suspended IC to the next resume, so writing it from a screen-off context would
 * silently do nothing.
 */
class WakeGestureService : Service() {

    private val handler = Handler(Looper.getMainLooper())

    private val settingObserver =
        object : ContentObserver(handler) {
            override fun onChange(selfChange: Boolean) {
                applySingleTapToWake()
            }
        }

    override fun onCreate() {
        super.onCreate()
        if (DEBUG) Log.d(TAG, "onCreate")

        // Apply before registering anything else: this is the one thing that must happen.
        applySingleTapToWake()

        contentResolver.registerContentObserver(
            Settings.Secure.getUriFor(SINGLE_TAP_TO_WAKE),
            false,
            settingObserver,
            UserHandle.USER_CURRENT,
        )
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    override fun onDestroy() {
        if (DEBUG) Log.d(TAG, "onDestroy")
        contentResolver.unregisterContentObserver(settingObserver)
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun applySingleTapToWake() {
        val enabled =
            Settings.Secure.getIntForUser(
                contentResolver,
                SINGLE_TAP_TO_WAKE,
                0,
                UserHandle.USER_CURRENT,
            ) != 0
        if (DEBUG) Log.d(TAG, "single tap to wake: $enabled")
        try {
            File(NODE_SINGLE_TAP_TO_WAKE).writeText(if (enabled) "1" else "0")
        } catch (e: IOException) {
            Log.e(TAG, "Failed to write $NODE_SINGLE_TAP_TO_WAKE", e)
        }
    }

    companion object {
        private const val TAG = "WakeGestureService"
        private val DEBUG = Log.isLoggable(TAG, Log.DEBUG)

        /**
         * Not a Settings.Secure constant: there is no AOSP consumer for single tap to wake, so
         * the key stays device-local rather than patched into frameworks/base.
         */
        const val SINGLE_TAP_TO_WAKE = "single_tap_to_wake"

        private const val NODE_SINGLE_TAP_TO_WAKE =
            "/sys/class/touch/touch_dev/single_tap_to_wake"

        fun startService(context: Context) {
            context.startServiceAsUser(
                Intent(context, WakeGestureService::class.java),
                UserHandle.CURRENT,
            )
        }
    }
}
