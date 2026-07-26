// ============================================================
// frontend/src/composables/useModeling.ts
// 统一建模生命周期 — Replay / Realtime 共用
//
// 设计与用法:
//   导出 useModeling({ yoloEnabled, saveReport, taskName })
//     start()   开始建模：读 localStorage → 创建两个引擎 → WS
//     stop()    停止建模：断开 WS → 清理引擎
//     running   是否正在建模
// ============================================================

import { ref, type Ref } from 'vue'
import { resetReconstruction } from '@/api/reconstruction'
import { resetEstimator } from '@/api/vehicle'
import { startReportSignal, stopReportSignal } from '@/api/report'
import { useEstimationStore } from '@/stores/estimation'

export function useModeling(options: {
  yoloEnabled: Ref<boolean>
  saveReport: Ref<boolean>
  taskName: Ref<string>
}) {
  const running = ref(false)
  const estStore = useEstimationStore()

  // WS 函数由调用方注入（避免循环依赖）
  let _wsConnect: () => void = () => {}
  let _wsDisconnect: () => void = () => {}

  function setWs(connect: () => void, disconnect: () => void) {
    _wsConnect = connect
    _wsDisconnect = disconnect
  }

  async function start() {
    // 1. 读前端保存的参数
    const reconCfg = JSON.parse(
      localStorage.getItem('suoxingtuan_recon_config') || '{}')
    const estCfg = JSON.parse(
      localStorage.getItem('suoxingtuan_est_config') || '{}')

    // 2. 创建重建引擎
    await resetReconstruction({
      ...reconCfg,
      yolo_enabled: options.yoloEnabled.value,
    })

    // 3. 创建位置估计器
    await resetEstimator({
      mode: estCfg.mode || 'bicycle',
      wheelbase: estCfg.wheelbase,
      constant_speed: estCfg.constant_speed,
      fusion_weight: estCfg.fusion_weight,
    })

    // 4. 同步到共享 store（供 useConnection 读模式）
    estStore.setConfig(estCfg)

    // 5. 可选 Report
    if (options.saveReport.value) {
      await startReportSignal(options.taskName.value || undefined)
    }

    // 6. 打开重建结果 WS
    _wsConnect()

    running.value = true
  }

  async function stop() {
    running.value = false
    _wsDisconnect()
    if (options.saveReport.value) {
      await stopReportSignal()
    }
    await resetReconstruction({})
    estStore.clear()
  }

  return { running, start, stop, setWs }
}
