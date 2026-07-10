<!-- ============================================================ -->
<!-- frontend/src/components/PointCloudViewer.vue                    -->
<!-- Three.js 点云实时渲染 — 按高度着色，OrbitControls 交互            -->
<!-- ============================================================ -->

<template>
  <div ref="containerRef" style="width: 100%; height: 100%; position: relative">
    <div style="position:absolute;top:8px;left:8px;background:rgba(0,0,0,0.65);padding:3px 8px;font-size:10px;color:#aaa;border-radius:3px;pointer-events:none">
      <div>点数: {{ pointCount.toLocaleString() }}</div>
      <div>范围: Z {{ zRange[0].toFixed(2) }} ~ {{ zRange[1].toFixed(2) }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

const containerRef = ref<HTMLElement | null>(null)
const pointCount = ref(0)
const zRange = ref<[number, number]>([0, 0])

let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let controls: OrbitControls
let pointsObj: THREE.Points | null = null
let animId = 0
let disposed = false

// ── 颜色映射: Z → RGB (蓝绿黄红渐变) ──
function zToColor(z: number, zMin: number, zMax: number): [number, number, number] {
  if (zMax - zMin < 0.001) return [0.5, 0.5, 0.5] // 无高差 → 灰色
  const t = Math.max(0, Math.min(1, (z - zMin) / (zMax - zMin)))
  // HSL 渐变: 240°(蓝) → 180°(青) → 120°(绿) → 60°(黄) → 0°(红)
  const hue = (1 - t) * 0.667 // hue: 0.667→0 (蓝到红)
  const color = new THREE.Color()
  color.setHSL(hue, 0.9, 0.55)
  return [color.r, color.g, color.b]
}

onMounted(() => {
  const el = containerRef.value!
  const w = el.clientWidth
  const h = el.clientHeight

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x1a1a1a)

  camera = new THREE.PerspectiveCamera(55, w / h, 0.01, 100)
  camera.position.set(3, 2, 3)
  camera.lookAt(0, 0, 0)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  el.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.15
  controls.target.set(0, 0, 0)

  // 参考网格 + 坐标轴
  scene.add(new THREE.GridHelper(5, 20, 0x333333, 0x222222))
  scene.add(new THREE.AxesHelper(1))

  window.addEventListener('resize', onResize)
  animId = requestAnimationFrame(loop)
})

onUnmounted(() => {
  disposed = true
  cancelAnimationFrame(animId)
  window.removeEventListener('resize', onResize)
  if (pointsObj) {
    pointsObj.geometry.dispose()
    ;(pointsObj.material as THREE.Material).dispose()
  }
  renderer?.dispose()
  controls?.dispose()
})

function onResize() {
  if (!containerRef.value) return
  const w = containerRef.value.clientWidth
  const h = containerRef.value.clientHeight
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
}

function loop() {
  if (disposed) return
  controls.update()
  renderer.render(scene, camera)
  animId = requestAnimationFrame(loop)
}

// ── 外部方法 ──

function updatePointCloud(points: number[]) {
  if (!points || points.length < 3) return

  const N = points.length / 3

  // 计算 Z 范围
  let zMin = Infinity, zMax = -Infinity
  for (let i = 0; i < points.length; i += 3) {
    const z = points[i + 2]
    if (z < zMin) zMin = z
    if (z > zMax) zMax = z
  }
  zRange.value = [zMin, zMax]

  // 生成颜色
  const colors = new Float32Array(points.length)
  for (let i = 0; i < points.length; i += 3) {
    const [r, g, b] = zToColor(points[i + 2], zMin, zMax)
    colors[i] = r
    colors[i + 1] = g
    colors[i + 2] = b
  }

  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(points), 3))
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))

  const mat = new THREE.PointsMaterial({
    size: 0.015,
    vertexColors: true,
    sizeAttenuation: true,
    blending: THREE.NormalBlending,
    depthWrite: true,
  })

  // 替换旧点云
  if (pointsObj) {
    pointsObj.geometry.dispose()
    ;(pointsObj.material as THREE.Material).dispose()
    scene.remove(pointsObj)
  }
  pointsObj = new THREE.Points(geo, mat)
  scene.add(pointsObj)

  pointCount.value = N
}

function resetView() {
  if (pointsObj) {
    pointsObj.geometry.dispose()
    ;(pointsObj.material as THREE.Material).dispose()
    scene.remove(pointsObj)
    pointsObj = null
  }
  pointCount.value = 0
  zRange.value = [0, 0]
}

defineExpose({ updatePointCloud, resetView })
</script>
