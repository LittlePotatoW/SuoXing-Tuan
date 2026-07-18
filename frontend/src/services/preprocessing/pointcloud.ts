// ============================================================
// frontend/src/services/preprocessing/pointcloud.ts
// 数据预处理层 (Layer 1.5)：深度图 16-bit PNG 翻转/裁剪
//
// 设计与用法:
//   导出 applyDepthPreprocess(b64)  → 按 config 处理, 返回 base64
//   导出 depthToGrayscale(b64)      → 16-bit → 8-bit 灰度图 base64
//   config 在 defaults.ts preprocess.depth
// ============================================================

import { preprocess } from '@/config/defaults'

export async function applyDepthPreprocess(b64: string): Promise<string> {
  const cfg = preprocess.depth

  if (cfg.flip === 'none' && !cfg.crop) return b64

  const img = await _b64ToImage(b64)
  const canvas = document.createElement('canvas')
  const w = img.width
  const h = img.height
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')!

  // flip
  if (cfg.flip === 'h' || cfg.flip === 'hv') {
    ctx.translate(w, 0); ctx.scale(-1, 1)
  }
  if (cfg.flip === 'v' || cfg.flip === 'hv') {
    ctx.translate(0, h); ctx.scale(1, -1)
  }
  ctx.drawImage(img, 0, 0)

  // crop
  if (cfg.crop) {
    const cropped = ctx.getImageData(cfg.crop.x, cfg.crop.y, cfg.crop.w, cfg.crop.h)
    canvas.width = cfg.crop.w
    canvas.height = cfg.crop.h
    canvas.getContext('2d')!.putImageData(cropped, 0, 0)
  }

  // 输出 PNG（无损保留 16-bit 需要特殊处理，浏览器 Canvas 只有 8-bit）
  // 这里用 PNG 输出保证格式一致，但精度降为 8-bit
  const dataUrl = canvas.toDataURL('image/png')
  const comma = dataUrl.indexOf(',')
  return dataUrl.slice(comma + 1)
}

export async function depthToGrayscale(b64: string): Promise<string> {
  const img = await _b64ToImage(b64)
  const canvas = document.createElement('canvas')
  canvas.width = img.width
  canvas.height = img.height
  const ctx = canvas.getContext('2d')!
  ctx.drawImage(img, 0, 0)

  // canvas 自动转为 8-bit，输出 JPEG 灰度图用于界面预览
  const dataUrl = canvas.toDataURL('image/jpeg', 0.8)
  const comma = dataUrl.indexOf(',')
  return dataUrl.slice(comma + 1)
}

function _b64ToImage(b64: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = `data:image/png;base64,${b64}`
  })
}
