package com.suoxingtuan.inspector.data.repository

import com.suoxingtuan.inspector.data.model.TaskData

/**
 * Task store — mirrors taskStore.ts module-level reactive singleton.
 */
object TaskRepository {
    val currentTask = TaskData()

    private val STATUS_LABELS = mapOf(
        "pending" to "待执行", "running" to "执行中", "done" to "已完成", "cancelled" to "已取消"
    )

    fun getStatusLabel(status: String): String = STATUS_LABELS[status] ?: status
}
