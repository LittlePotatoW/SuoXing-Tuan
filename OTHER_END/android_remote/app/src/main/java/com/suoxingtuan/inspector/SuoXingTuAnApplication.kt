package com.suoxingtuan.inspector

import android.app.Application
import com.suoxingtuan.inspector.data.local.Preferences

class SuoXingTuAnApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        Preferences.init(this)
    }
}
