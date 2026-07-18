// ============================================================
// frontend/src/utils/math.ts
// 数学工具：角度弧度互转
//
// 设计与用法:
//   导出 degToRad(deg)  度 → 弧度
//   导出 radToDeg(rad)  弧度 → 度
// ============================================================

export function degToRad(deg: number): number {
  return (deg * Math.PI) / 180
}

export function radToDeg(rad: number): number {
  return (rad * 180) / Math.PI
}
