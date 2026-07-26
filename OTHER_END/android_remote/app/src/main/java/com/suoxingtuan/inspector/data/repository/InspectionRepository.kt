package com.suoxingtuan.inspector.data.repository

import com.suoxingtuan.inspector.data.local.Preferences
import com.suoxingtuan.inspector.data.model.*

/**
 * Inspection records repository — mirrors inspectionStore.ts.
 */
object InspectionRepository {
    private const val KEY = "inspection_records"

    val BRANCHES = listOf(
        BranchDef("civil", "土建结构", "hammer"),
        BranchDef("track", "轨道检测", "map"),
        BranchDef("equipment", "设备检测", "tool")
    )

    val RISK_CONFIG: Map<RiskLevel, RiskConfig> = mapOf(
        RiskLevel.high to RiskConfig("高风险", "#EF4444"),
        RiskLevel.medium to RiskConfig("中风险", "#F2994A"),
        RiskLevel.normal to RiskConfig("普通", "#8E8E8E")
    )

    val STATUS_CONFIG: Map<IssueStatus, StatusConfig> = mapOf(
        IssueStatus.pending to StatusConfig("待处理", "#FFF3E0", "#E65100"),
        IssueStatus.reviewed to StatusConfig("已复核", "#E8F5E9", "#2E7D32"),
        IssueStatus.high_risk to StatusConfig("高风险", "#FFEBEE", "#C62828"),
        IssueStatus.normal to StatusConfig("一般", "#F5F5F5", "#616161")
    )

    private val SAMPLE_DATA = listOf(
        InspectionIssue("1", "civil", "裂缝检测", "K12+350 拱顶", "2026-07-09", RiskLevel.high, IssueStatus.pending, "2026-07-09T08:30:00Z"),
        InspectionIssue("2", "civil", "渗漏水", "K12+400 侧墙", "2026-07-09", RiskLevel.medium, IssueStatus.reviewed, "2026-07-09T09:15:00Z"),
        InspectionIssue("3", "track", "扣件缺失", "K12+420", "2026-07-09", RiskLevel.high, IssueStatus.high_risk, "2026-07-09T10:00:00Z"),
        InspectionIssue("4", "equipment", "管线支架松脱", "K11+800", "2026-07-08", RiskLevel.normal, IssueStatus.normal, "2026-07-08T14:20:00Z")
    )

    fun getIssues(): List<InspectionIssue> {
        val stored = Preferences.getObject<List<InspectionIssue>>(KEY)
        return if (stored.isNullOrEmpty()) {
            Preferences.setObject(KEY, SAMPLE_DATA)
            SAMPLE_DATA
        } else stored
    }

    private fun saveIssues(issues: List<InspectionIssue>) = Preferences.setObject(KEY, issues)

    fun addIssue(issue: InspectionIssue): InspectionIssue {
        val issues = getIssues().toMutableList()
        val newIssue = issue.copy(id = System.currentTimeMillis().toString(), createdAt = java.time.Instant.now().toString())
        issues.add(newIssue)
        saveIssues(issues)
        return newIssue
    }

    fun deleteIssue(id: String) = saveIssues(getIssues().filter { it.id != id })

    fun getDateGroups(): List<DateGroup> {
        return getIssues().groupBy { it.date }
            .map { (date, issues) -> DateGroup(date, issues) }
            .sortedByDescending { it.date }
    }

    fun getIssuesByDate(date: String): List<Pair<BranchDef, List<InspectionIssue>>> {
        val issues = getIssues().filter { it.date == date }
        return BRANCHES.map { b -> b to issues.filter { it.branch == b.key } }.filter { it.second.isNotEmpty() }
    }

    fun formatDateShort(dateStr: String): String {
        val parts = dateStr.split("-")
        if (parts.size != 3) return dateStr
        return "${parts[1].toInt()}月${parts[2].toInt()}日"
    }

    fun formatDateFull(dateStr: String): String {
        val parts = dateStr.split("-")
        if (parts.size != 3) return dateStr
        return "${parts[0]}年${parts[1]}月${parts[2]}日"
    }

    fun getTodayStr(): String {
        val d = java.time.LocalDate.now()
        return d.toString()
    }
}
