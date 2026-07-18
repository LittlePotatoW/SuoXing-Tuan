// ============================================================
// frontend/src/services/preprocessing/image.ts
// 数据预处理层 (Layer 1.5)：RGB JPEG 翻转/裁剪/缩放
//
// 设计与用法:
//   导出 applyImagePreprocess(b64)  → 按 config 处理, 返回 base64
//   config 在 defaults.ts preprocess.image
// ============================================================

import { preprocess } from '@/config/defaults'

export async function applyImagePreprocess(b64: string): Promise<string> {
  const cfg = preprocess.image

  // 无需处理
  if (cfg.flip === 'none' && !cfg.crop && !cfg.resize) return b64

  const img = await _b64ToImage(b64)
  const canvas = document.createElement('canvas')
  let w = img.width
  let h = img.height

  // crop 先于 resize
  if (cfg.crop) {
    w = cfg.crop.w
    h = cfg.crop.h
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')!
    ctx.drawImage(img, cfg.crop.x, cfg.crop.y, w, h, 0, 0, w, h)
  } else if (cfg.resize) {
    w = cfg.resize.w
    h = cfg.resize.h
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')!
    ctx.drawImage(img, 0, 0, w, h)
  } else {
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')!

    // flip
    ctx.save()
    if (cfg.flip === 'h' || cfg.flip === 'hv') {
      ctx.translate(w, 0)
      ctx.scale(-1, 1)
    }
    if (cfg.flip === 'v' || cfg.flip === 'hv') {
      ctx.translate(0, h)
      ctx.scale(1, -1)
    }
    ctx.drawImage(img, 0, 0)
    ctx.restore()
  }

  const dataUrl = canvas.toDataURL('image/jpeg', cfg.quality)
  const comma = dataUrl.indexOf(',')
  return dataUrl.slice(comma + 1)
}

function _b64ToImage(b64: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = `data:image/jpeg;base64,${b64}`
  })
}
