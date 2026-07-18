// ============================================================
// frontend/src/stores/vehicle.ts
// Pinia: 小车实时数据 — 速度、转向角、当前位置
//
// 设计与用法:
//   导出 useVehicleStore()
//     position / speed / steeringAngle (响应式)
//     updatePosition() / updateTelemetry()  更新数据
// ============================================================

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Position } from '@/types/data'

export const useVehicleStore = defineStore('vehicle', () => {
  const position = ref<Position>({ timestamp: 0, x: 0, y: 0, heading: 0 })
  const speed = ref(0)
  const steeringAngle = ref(0)

  function updatePosition(pos: Position) {
    position.value = pos
  }

  function updateTelemetry(spd: number, steer: number) {
    speed.value = spd
    steeringAngle.value = steer
  }

  return { position, speed, steeringAngle, updatePosition, updateTelemetry }
})
