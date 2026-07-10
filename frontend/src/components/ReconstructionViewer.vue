<!-- ============================================================ -->
<!-- frontend/src/components/ReconstructionViewer.vue                 -->
<!-- Three.js 3D 查看器 — 渲染 Mesh + 相机轨迹 + 裂缝标注            -->
<!-- ============================================================ -->

<template>
  <div ref="containerRef" style="width: 100%; height: 100%" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

const containerRef = ref<HTMLElement | null>(null)

let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let controls: OrbitControls
let meshGroup: THREE.Group
let trailGroup: THREE.Group
let crackGroup: THREE.Group
let animId = 0
let disposed = false

onMounted(() => {
  const el = containerRef.value!
  const w = el.clientWidth
  const h = el.clientHeight

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x1a1a1a)

  camera = new THREE.PerspectiveCamera(60, w / h, 0.01, 100)
  camera.position.set(2, 1.5, 2)
  camera.lookAt(0, 0, 0)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(w, h)
  renderer.setPixelRatio(window.devicePixelRatio)
  el.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true

  meshGroup = new THREE.Group()
  scene.add(meshGroup)

  trailGroup = new THREE.Group()
  scene.add(trailGroup)

  crackGroup = new THREE.Group()
  scene.add(crackGroup)

  // 参考网格 + 坐标轴
  scene.add(new THREE.GridHelper(5, 20, 0x444444, 0x333333))
  scene.add(new THREE.AxesHelper(1))

  // 光照（一次性添加到 scene，不随 mesh 更新销毁）
  scene.add(new THREE.AmbientLight(0xffffff, 0.7))
  const d1 = new THREE.DirectionalLight(0xffffff, 0.9)
  d1.position.set(2, 4, 3)
  scene.add(d1)
  const d2 = new THREE.DirectionalLight(0xffffff, 0.5)
  d2.position.set(-2, -1, -2)
  scene.add(d2)

  // 响应窗口大小变化
  window.addEventListener('resize', onResize)

  animId = requestAnimationFrame(loop)
})

onUnmounted(() => {
  disposed = true
  cancelAnimationFrame(animId)
  window.removeEventListener('resize', onResize)
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

function resetScene() {
  // 清理 meshGroup（geometry + material）
  meshGroup.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      child.geometry?.dispose()
      if (Array.isArray(child.material)) {
        child.material.forEach(m => m.dispose())
      } else {
        child.material?.dispose()
      }
    }
  })
  meshGroup.clear()

  // 清理 crackGroup
  crackGroup.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      child.geometry?.dispose()
      if (Array.isArray(child.material)) {
        child.material.forEach(m => m.dispose())
      } else {
        child.material?.dispose()
      }
    }
  })
  crackGroup.clear()

  // 清理 trailGroup
  trailGroup.traverse((child) => {
    if (child instanceof THREE.Line) {
      child.geometry?.dispose()
      if (Array.isArray(child.material)) {
        child.material.forEach(m => m.dispose())
      } else {
        child.material?.dispose()
      }
    }
  })
  trailGroup.clear()
}

function addMesh(data: { vertices: number[]; faces: number[]; vertex_count: number; face_count: number; vertex_colors?: number[] } | null) {
  if (!data || !data.vertices.length) return

  // 先清理旧 mesh，防止 GPU 内存泄漏
  resetScene()

  const geo = new THREE.BufferGeometry()
  const verts = new Float32Array(data.vertices)
  geo.setAttribute('position', new THREE.BufferAttribute(verts, 3))

  if (data.faces.length > 0) {
    geo.setIndex(data.faces)
    geo.computeVertexNormals()
  }

  if (data.vertex_colors && data.vertex_colors.length === data.vertex_count * 3) {
    const colors = new Uint8Array(data.vertex_colors)
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3, true))
  }

  const mat = new THREE.MeshStandardMaterial({
    vertexColors: true,
    side: THREE.DoubleSide,
    roughness: 0.6,
    metalness: 0.0,
  })
  const mesh = new THREE.Mesh(geo, mat)
  meshGroup.add(mesh)

  // 线框用独立 geometry 拷贝，避免与实体 mesh 共享导致 dispose 冲突
  const wireGeo = geo.clone()
  const wireMat = new THREE.MeshBasicMaterial({ color: 0x666666, wireframe: true })
  const wire = new THREE.Mesh(wireGeo, wireMat)
  meshGroup.add(wire)
}

function updateTrail(trail: number[][] | null) {
  trailGroup.clear()
  if (!trail || trail.length < 2) return

  const points = trail.map(p => new THREE.Vector3(p[0], p[1], p[2]))
  const geo = new THREE.BufferGeometry().setFromPoints(points)
  const mat = new THREE.LineBasicMaterial({ color: 0x4fc3f7 })
  trailGroup.add(new THREE.Line(geo, mat))
}

function addCracks(cracks: { position: { x: number; y: number; z: number }; confidence: number; crack_type: string }[]) {
  crackGroup.clear()
  if (!cracks || !cracks.length) return

  for (const c of cracks) {
    const size = 0.03 + c.confidence * 0.04
    const geo = new THREE.SphereGeometry(size, 8, 8)
    const color = c.crack_type === '裂缝' || c.crack_type === 'crack' ? 0xef5350
      : c.crack_type === '渗漏' || c.crack_type === 'leakage' ? 0x42a5f5
      : 0xffa726
    const mat = new THREE.MeshBasicMaterial({ color })
    const sphere = new THREE.Mesh(geo, mat)
    sphere.position.set(c.position.x, c.position.y, c.position.z)
    crackGroup.add(sphere)
  }
}

defineExpose({ addMesh, updateTrail, resetScene, addCracks })
</script>
