/**
 * Inspection records store — manages issue data with local persistence.
 * In production, this would sync with a backend database linked to 3D models.
 */
import { getStorage, setStorage } from './storage'

// ---- Types ----
export type RiskLevel = 'high' | 'medium' | 'normal'
export type IssueStatus = 'pending' | 'reviewed' | 'high_risk' | 'normal'

export interface InspectionIssue {
  id: string
  branch: 'civil' | 'track' | 'equipment'
  title: string
  location: string
  date: string // "2026-07-09"
  risk: RiskLevel
  status: IssueStatus
  createdAt: string
}

export interface DateGroup {
  date: string
  issues: InspectionIssue[]
}

// ---- Risk & Status config ----
export const RISK_CONFIG: Record<RiskLevel, { label: string; color: string }> = {
  high: { label: '高风险', color: '#EF4444' },
  medium: { label: '中风险', color: '#F2994A' },
  normal: { label: '普通', color: '#8E8E8E' },
}

export const STATUS_CONFIG: Record<IssueStatus, { label: string; bg: string; color: string }> = {
  pending: { label: '待处理', bg: '#FFF3E0', color: '#E65100' },
  reviewed: { label: '已复核', bg: '#E8F5E9', color: '#2E7D32' },
  high_risk: { label: '高风险', bg: '#FFEBEE', color: '#C62828' },
  normal: { label: '一般', bg: '#F5F5F5', color: '#616161' },
}

// ---- Branch config ----
export const BRANCHES = [
  { key: 'civil' as const, name: '土建结构', icon: 'hammer' },
  { key: 'track' as const, name: '轨道检测', icon: 'map' },
  { key: 'equipment' as const, name: '设备检测', icon: 'tool' },
]

// ---- Storage key ----
const INSPECTION_KEY = 'inspection_records'

// ---- Sample data ----
const SAMPLE_DATA: InspectionIssue[] = [
  {
    id: '1',
    branch: 'civil',
    title: '裂缝检测',
    location: 'K12+350 拱顶',
    date: '2026-07-09',
    risk: 'high',
    status: 'pending',
    createdAt: '2026-07-09T08:30:00Z',
  },
  {
    id: '2',
    branch: 'civil',
    title: '渗漏水',
    location: 'K12+400 侧墙',
    date: '2026-07-09',
    risk: 'medium',
    status: 'reviewed',
    createdAt: '2026-07-09T09:15:00Z',
  },
  {
    id: '3',
    branch: 'track',
    title: '扣件缺失',
    location: 'K12+420',
    date: '2026-07-09',
    risk: 'high',
    status: 'high_risk',
    createdAt: '2026-07-09T10:00:00Z',
  },
  {
    id: '4',
    branch: 'equipment',
    title: '管线支架松脱',
    location: 'K11+800',
    date: '2026-07-08',
    risk: 'normal',
    status: 'normal',
    createdAt: '2026-07-08T14:20:00Z',
  },
]

/** Get all issues, initializing with sample data if empty. */
export function getIssues(): InspectionIssue[] {
  let stored = getStorage<InspectionIssue[]>(INSPECTION_KEY)
  if (!stored || stored.length === 0) {
    stored = [...SAMPLE_DATA]
    setStorage(INSPECTION_KEY, stored)
  }
  return stored
}

/** Save all issues. */
function saveIssues(issues: InspectionIssue[]): void {
  setStorage(INSPECTION_KEY, issues)
}

/** Add a new issue. */
export function addIssue(
  issue: Omit<InspectionIssue, 'id' | 'createdAt'> & { risk?: RiskLevel; status?: IssueStatus },
): InspectionIssue {
  const issues = getIssues()
  const newIssue: InspectionIssue = {
    ...issue,
    risk: issue.risk || 'normal',
    status: issue.status || 'pending',
    id: String(Date.now()),
    createdAt: new Date().toISOString(),
  }
  issues.push(newIssue)
  saveIssues(issues)
  return newIssue
}

/** Delete an issue by id. */
export function deleteIssue(id: string): void {
  const issues = getIssues().filter((i) => i.id !== id)
  saveIssues(issues)
}

/**
 * Group issues by date, sorted descending.
 * Only returns dates that have at least one issue.
 */
export function getDateGroups(): DateGroup[] {
  const issues = getIssues()
  const map = new Map<string, InspectionIssue[]>()

  for (const issue of issues) {
    const list = map.get(issue.date) || []
    list.push(issue)
    map.set(issue.date, list)
  }

  return Array.from(map.entries())
    .map(([date, issues]) => ({ date, issues }))
    .sort((a, b) => b.date.localeCompare(a.date))
}

/** Get issues for a specific date, grouped by branch. */
export function getIssuesByDate(date: string) {
  const issues = getIssues().filter((i) => i.date === date)
  return BRANCHES.map((branch) => ({
    ...branch,
    issues: issues.filter((i) => i.branch === branch.key),
  })).filter((b) => b.issues.length > 0)
}

/** Format "2026-07-09" → "07月09日" */
export function formatDateShort(dateStr: string): string {
  const parts = dateStr.split('-')
  if (parts.length !== 3) return dateStr
  return `${parseInt(parts[1])}月${parseInt(parts[2])}日`
}

/** Format "2026-07-09" → "2026年07月09日" */
export function formatDateFull(dateStr: string): string {
  const parts = dateStr.split('-')
  if (parts.length !== 3) return dateStr
  return `${parts[0]}年${parts[1]}月${parts[2]}日`
}

/** Get today's date string "2026-07-09" */
export function getTodayStr(): string {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
