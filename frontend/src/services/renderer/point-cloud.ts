// ============================================================
// frontend/src/services/renderer/point-cloud.ts
// 点云 / Mesh 渲染：PLY 解析(ASCII+Binary) + 自适应渲染
//
// 设计与用法:
//   导出 parsePly(data) → { vertices, faces | null, colors | null }
//   导出 fetchAndParsePly(url) → Promise<PlyData>
//   导出 addToScene(ply, sceneMgr)
// ============================================================

import * as THREE from 'three'
import { httpClient } from '@/network/http-client'
import type { SceneManager } from './three-scene'

export interface PlyData {
  vertices: Float32Array
  faces: Uint32Array | null
  colors: Uint8Array | null   // 顶点颜色 [r,g,b, ...], 可能为 null
}

/** 解析 PLY 文件（自动识别 ASCII / binary little-endian） */
export async function parsePly(data: ArrayBuffer): Promise<PlyData> {
  const header = _readHeader(data)
  console.log('[PLY] header:', { format: header.format, vertexCount: header.vertexCount, faceCount: header.faceCount, vertStride: header.vertStride, hasColor: header.hasColor, headerEnd: header.headerEnd })
  let result: PlyData
  if (header.format.startsWith('binary_little_endian')) {
    result = _parseBinary(data, header)
  } else {
    result = _parseAscii(new TextDecoder().decode(data), header)
  }
  console.log('[PLY] result:', { vertLen: result.vertices.length, faceLen: result.faces?.length, colorLen: result.colors?.length, isMesh: !!(result.faces && result.faces.length > 0) })
  return result
}

/** fetch PLY 文件并解析 */
export async function fetchAndParsePly(url: string): Promise<PlyData> {
  const fullUrl = url.startsWith('http') ? url : (httpClient.defaults.baseURL ?? '') + url
  const resp = await fetch(fullUrl)
  if (!resp.ok) throw new Error(`PLY fetch failed: ${resp.status}`)
  return parsePly(await resp.arrayBuffer())
}

// ---- header 解析 ----

interface PlyHeader {
  format: string
  vertexCount: number
  faceCount: number
  hasColor: boolean
  vertStride: number   // 每个顶点占多少字节（含法线等额外属性）
  headerEnd: number
}

function _readHeader(buf: ArrayBuffer): PlyHeader {
  const text = new TextDecoder().decode(buf.slice(0, Math.min(4096, buf.byteLength)))
  console.log('[PLY] === raw header ===\n' + text.split('\n').slice(0, 25).join('\n') + '\n=== end header ===')
  const lines = text.split('\n')

  let format = ''
  let vertexCount = 0
  let faceCount = 0
  let hasColor = false
  let vertStride = 0
  let inVertex = false
  let headerEnd = 0

  for (const line of lines) {
    headerEnd += line.length + 1
    const t = line.trim()
    if (t.startsWith('format ')) {
      format = t.split(/\s+/)[1] + '_' + (t.split(/\s+/)[2] || '')
    }
    if (t.startsWith('element vertex')) {
      vertexCount = parseInt(t.split(/\s+/)[2], 10)
      inVertex = true
      vertStride = 0
    }
    if (t.startsWith('element face')) {
      faceCount = parseInt(t.split(/\s+/)[2], 10)
      inVertex = false
    }
    if (inVertex) {
      if (t.startsWith('property float') || t.startsWith('property double')) vertStride += 4
      if (t.startsWith('property uchar')) { vertStride += 1; hasColor = true }
      if (t.startsWith('property int')) vertStride += 4
    }
    if (t === 'end_header') break
  }

  return { format, vertexCount, faceCount, hasColor, vertStride, headerEnd }
}

// ---- ASCII 解析 ----

function _parseAscii(text: string, h: PlyHeader): PlyData {
  const lines = text.split('\n')
  let inHeader = true
  const vs: number[] = []
  const fs: number[] = []
  const cs: number[] = []

  for (const line of lines) {
    const t = line.trim()
    if (!t) continue
    if (inHeader) { if (t === 'end_header') inHeader = false; continue }

    if (vs.length / 3 < h.vertexCount) {
      const p = t.split(/\s+/).map(Number)
      vs.push(p[0], p[1], p[2])
      if (h.hasColor && p.length >= 6) cs.push(p[3], p[4], p[5])
    } else if (h.faceCount > 0 && fs.length / 3 < h.faceCount) {
      const p = t.split(/\s+/).map(Number)
      const cnt = p[0]
      if (cnt >= 3) { fs.push(p[1], p[2], p[3]); if (cnt === 4) fs.push(p[1], p[3], p[4]) }
    }
  }

  return {
    vertices: new Float32Array(vs),
    faces: fs.length > 0 ? new Uint32Array(fs) : null,
    colors: cs.length > 0 ? new Uint8Array(cs) : null,
  }
}

// ---- 二进制解析 ----

function _parseBinary(buf: ArrayBuffer, h: PlyHeader): PlyData {
  const dv = new DataView(buf)
  let offset = h.headerEnd

  // 用 header 中计算的步长（含法线等额外属性），只取前 3 个 float 作为 xyz
  const vs = new Float32Array(h.vertexCount * 3)
  const cs = h.hasColor ? new Uint8Array(h.vertexCount * 3) : null
  const colorOffset = h.vertStride - (h.hasColor ? 3 : 0) // uchar 在最后

  for (let i = 0; i < h.vertexCount; i++) {
    const vi = i * 3
    vs[vi]     = dv.getFloat32(offset, true)
    vs[vi + 1] = dv.getFloat32(offset + 4, true)
    vs[vi + 2] = dv.getFloat32(offset + 8, true)
    if (cs) {
      cs[vi]     = dv.getUint8(offset + colorOffset)
      cs[vi + 1] = dv.getUint8(offset + colorOffset + 1)
      cs[vi + 2] = dv.getUint8(offset + colorOffset + 2)
    }
    offset += h.vertStride
  }

  // 面: 每面 1 byte count + 3~4 * 4 bytes indices
  const fs: number[] = []
  for (let i = 0; i < h.faceCount; i++) {
    const cnt = dv.getUint8(offset)
    offset += 1
    const i1 = dv.getUint32(offset, true)
    const i2 = dv.getUint32(offset + 4, true)
    const i3 = dv.getUint32(offset + 8, true)
    fs.push(i1, i2, i3)
    if (i < 5) console.log(`[PLY] face[${i}]: cnt=${cnt} indices=[${i1},${i2},${i3}] vertexCount=${h.vertexCount}`)
    if (cnt === 4) {
      const i4 = dv.getUint32(offset + 12, true)
      fs.push(i1, i3, i4)
    }
    offset += cnt * 4
  }

  // 采样顶点
  console.log('[PLY] vertex[0]:', [vs[0], vs[1], vs[2]], 'vertex[1]:', [vs[3], vs[4], vs[5]],
    'vertex[last]:', [vs[vs.length-3], vs[vs.length-2], vs[vs.length-1]])
  let nanCount = 0
  for (let i = 0; i < vs.length; i++) { if (isNaN(vs[i])) nanCount++ }
  console.log(`[PLY] NaN in vertices: ${nanCount}/${vs.length}`)

  return {
    vertices: vs,
    faces: fs.length > 0 ? new Uint32Array(fs) : null,
    colors: cs,
  }
}

// ---- 脏检查缓存（避免每次轮询都全量重建几何体） ----

interface _DirtyCache {
  vertByteLength: number
  vertHead: number   // 前 6 个 float 的校验和
  vertTail: number   // 末 6 个 float 的校验和
  faceLen: number
  colorLen: number
}

let _lastCache: _DirtyCache | null = null

function _isDirty(ply: PlyData): boolean {
  if (!_lastCache) return true
  const v = ply.vertices
  const head = v[0] + v[1] + v[2] + v[3] + v[4] + v[5]
  const n = v.length
  const tail = n >= 6 ? v[n - 6] + v[n - 5] + v[n - 4] + v[n - 3] + v[n - 2] + v[n - 1] : 0
  return (
    v.byteLength !== _lastCache.vertByteLength ||
    head !== _lastCache.vertHead ||
    tail !== _lastCache.vertTail ||
    (ply.faces?.length ?? 0) !== _lastCache.faceLen ||
    (ply.colors?.length ?? 0) !== _lastCache.colorLen
  )
}

function _updateCache(ply: PlyData): void {
  const v = ply.vertices
  const n = v.length
  _lastCache = {
    vertByteLength: v.byteLength,
    vertHead: v[0] + v[1] + v[2] + v[3] + v[4] + v[5],
    vertTail: n >= 6 ? v[n - 6] + v[n - 5] + v[n - 4] + v[n - 3] + v[n - 2] + v[n - 1] : 0,
    faceLen: ply.faces?.length ?? 0,
    colorLen: ply.colors?.length ?? 0,
  }
}

// ---- Three.js 渲染 ----

/**
 * 添加数据到场景，自动选择渲染模式
 * 坐标变换: (x, y, z) → (x, z, -y)
 */
export function addToScene(ply: PlyData, sceneMgr: SceneManager): void {
  // 数据未变化则跳过，避免每 2 秒轮询时画面闪烁
  if (!_isDirty(ply)) return
  _updateCache(ply)

  // 清旧数据
  sceneMgr.cloudGroup.traverse((child) => {
    if (child instanceof THREE.Points || child instanceof THREE.Mesh) {
      child.geometry?.dispose()
      const mats = Array.isArray(child.material) ? child.material : [child.material]
      mats.forEach((m) => (m as THREE.Material).dispose())
    }
  })
  sceneMgr.cloudGroup.clear()

  if (ply.vertices.length < 3) return

  const rawLen = ply.vertices.length / 3
  const cleanV: number[] = []
  const cleanC: number[] = []
  for (let i = 0; i < rawLen; i++) {
    const x = ply.vertices[i * 3]
    const y = ply.vertices[i * 3 + 1]
    const z = ply.vertices[i * 3 + 2]
    if (!isFinite(x) || !isFinite(y) || !isFinite(z)) continue
    cleanV.push(x, z, -y)
    if (ply.colors) {
      cleanC.push(ply.colors[i * 3], ply.colors[i * 3 + 1], ply.colors[i * 3 + 2])
    }
  }
  if (cleanV.length < 3) return
  const verts = new Float32Array(cleanV)

  console.log('[PLY] addToScene:', { vertCount: cleanV.length / 3, faceCount: ply.faces ? ply.faces.length / 3 : 0, mode: ply.faces && ply.faces.length > 0 ? 'MESH' : 'POINT' })
  // 采样变换后的顶点
  console.log('[PLY] scene vert[0]:', [cleanV[0], cleanV[1], cleanV[2]],
    'vert[last]:', [cleanV[cleanV.length-3], cleanV[cleanV.length-2], cleanV[cleanV.length-1]])
  // 包围盒
  let [minX, minY, minZ] = [Infinity, Infinity, Infinity]
  let [maxX, maxY, maxZ] = [-Infinity, -Infinity, -Infinity]
  for (let i = 0; i < cleanV.length; i += 3) {
    if (cleanV[i] < minX) minX = cleanV[i]
    if (cleanV[i] > maxX) maxX = cleanV[i]
    if (cleanV[i+1] < minY) minY = cleanV[i+1]
    if (cleanV[i+1] > maxY) maxY = cleanV[i+1]
    if (cleanV[i+2] < minZ) minZ = cleanV[i+2]
    if (cleanV[i+2] > maxZ) maxZ = cleanV[i+2]
  }
  console.log('[PLY] bbox min:', [minX, minY, minZ], 'max:', [maxX, maxY, maxZ],
    'center:', [(minX+maxX)/2, (minY+maxY)/2, (minZ+maxZ)/2],
    'diag:', [maxX-minX, maxY-minY, maxZ-minZ])

  if (ply.faces && ply.faces.length > 0) {
    // === Mesh 模式 ===
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(verts, 3))
    geo.setIndex(new THREE.BufferAttribute(ply.faces, 1))
    geo.computeVertexNormals()

    const hasVC = ply.colors && ply.colors.length > 0
    if (hasVC) {
      geo.setAttribute('color', new THREE.BufferAttribute(new Uint8Array(cleanC), 3, true))
    }

    const matSolid = new THREE.MeshStandardMaterial({
      color: hasVC ? 0xffffff : 0x808080,
      side: THREE.DoubleSide,
      roughness: 0.6,
      metalness: 0.0,
      vertexColors: !!hasVC,
    })
    sceneMgr.cloudGroup.add(new THREE.Mesh(geo, matSolid))

    const matWire = new THREE.MeshBasicMaterial({
      color: 0x666666, wireframe: true,
    })
    sceneMgr.cloudGroup.add(new THREE.Mesh(geo, matWire))
  } else {
    // === 点云模式 ===
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(verts, 3))
    if (ply.colors && ply.colors.length > 0) {
      geo.setAttribute('color', new THREE.BufferAttribute(new Uint8Array(cleanC), 3, true))
    }
    const hasVC = ply.colors && ply.colors.length > 0
    const mat = new THREE.PointsMaterial({
      color: hasVC ? 0xffffff : 0xaaaaaa,
      size: 0.015,
      vertexColors: !!hasVC,
    })
    sceneMgr.cloudGroup.add(new THREE.Points(geo, mat))
  }
}
