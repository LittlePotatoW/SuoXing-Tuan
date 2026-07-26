import { reactive } from 'vue'

export interface TaskIssue {
  id: string
  title: string
  location: string
  riskColor: string
  date: string
}

export interface TaskData {
  id: string
  name: string
  area: string
  planStart: string
  planEnd: string
  status: 'pending' | 'running' | 'done' | 'cancelled'
  progress: number
  doneDist: number
  totalDist: number
  robotPos: string
  robotBattery: number
  robotSpeed: number
  robotStatus: string
  nextPoint: string
  timeRemaining: string
  issues: TaskIssue[]
}

export const currentTask = reactive<TaskData>({
  id: 'TD-2026-0711-001',
  name: '隧道B区巡检',
  area: '隧道B区 (K12+200 ~ K12+800)',
  planStart: '2026-07-11 14:00',
  planEnd: '2026-07-11 16:00',
  status: 'running',
  progress: 65,
  doneDist: 0.39,
  totalDist: 0.6,
  robotPos: 'K12+456',
  robotBattery: 78,
  robotSpeed: 1.2,
  robotStatus: '运行中',
  nextPoint: '消防通道 #2',
  timeRemaining: '01:28:36',
  issues: [
    { id: 'i1', title: '裂缝宽度超标 3mm', location: 'K12+350 拱顶', riskColor: '#EF4444', date: '2026-07-11' },
    { id: 'i2', title: '渗漏水痕迹', location: 'K12+400 侧墙', riskColor: '#F2994A', date: '2026-07-11' },
    { id: 'i3', title: '扣件松动', location: 'K12+420 左轨', riskColor: '#8E8E8E', date: '2026-07-11' },
  ],
})

const STATUS_LABELS: Record<string, string> = { pending: '待执行', running: '执行中', done: '已完成', cancelled: '已取消' }

export function getStatusLabel(status: string): string {
  return STATUS_LABELS[status] || status
}
