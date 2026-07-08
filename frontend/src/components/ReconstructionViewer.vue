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

  // 参考网格 + 坐标轴
  scene.add(new THREE.GridHelper(5, 20, 0x444444, 0x333333))
  scene.add(new THREE.AxesHelper(1))

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

function updateMesh(data: { vertices: number[]; faces: number[]; vertex_count: number; face_count: number; vertex_colors?: number[] } | null) {
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
  if (!data || !data.vertices.length) return

  const geo = new THREE.BufferGeometry()
  const verts = new Float32Array(data.vertices)
  geo.setAttribute('position', new THREE.BufferAttribute(verts, 3))

  if (data.faces.length > 0) {
    geo.setIndex(data.faces)
    geo.computeVertexNormals()
  }

  // 顶点颜色
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

  // 线框叠加，方便辨认几何结构
  const wireMat = new THREE.MeshBasicMaterial({ color: 0x666666, wireframe: true })
  const wire = new THREE.Mesh(geo, wireMat)
  meshGroup.add(wire)

  // 光照
  const ambient = new THREE.AmbientLight(0xffffff, 0.7)
  const d1 = new THREE.DirectionalLight(0xffffff, 0.9)
  d1.position.set(2, 4, 3)
  const d2 = new THREE.DirectionalLight(0xffffff, 0.5)
  d2.position.set(-2, -1, -2)
  meshGroup.add(ambient, d1, d2)
}

function updateTrail(trail: number[][] | null) {
  trailGroup.clear()
  if (!trail || trail.length < 2) return

  const points = trail.map(p => new THREE.Vector3(p[0], p[1], p[2]))
  const geo = new THREE.BufferGeometry().setFromPoints(points)
  const mat = new THREE.LineBasicMaterial({ color: 0x4fc3f7 })
  trailGroup.add(new THREE.Line(geo, mat))
}

defineExpose({ updateMesh, updateTrail })
</script>
