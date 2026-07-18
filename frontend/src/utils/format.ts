// ============================================================
// frontend/src/utils/format.ts
// 数据格式化工具
//
// 设计与用法:
//   导出 round(v, n)  保留 n 位小数
//   导出 timeStr(ts)  Unix 时间戳 → HH:MM:SS
// ============================================================

/** 保留 n 位小数 */
export function round(v: number, n = 2): number {
  return Math.round(v * 10 ** n) / 10 ** n
}

/** Unix 时间戳 → HH:MM:SS */
export function timeStr(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString()
}
