// ============================================================
// frontend/src/services/renderer/three-scene.ts
// Three.js 场景管理器：场景/相机/光照/OrbitControls/WASD/Group
//
// 设计与用法:
//   导出 SceneManager 类
//   new SceneManager(canvas) → animate() → dispose()
//   cloudGroup / trailGroup / crackGroup 供外部模块添加内容
// ============================================================

import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

const MOVE_SPEED = 0.8

export class SceneManager {
  scene: THREE.Scene
  camera: THREE.PerspectiveCamera
  renderer: THREE.WebGLRenderer
  controls: OrbitControls

  cloudGroup: THREE.Group
  trailGroup: THREE.Group
  crackGroup: THREE.Group

  private _canvas: HTMLCanvasElement
  private _animationId: number | null = null
  private _disposed = false
  private _lastTime = 0
  private _keysDown = new Set<string>()

  private _onKeyDown: ((e: KeyboardEvent) => void) | null = null
  private _onKeyUp: ((e: KeyboardEvent) => void) | null = null

  constructor(canvas: HTMLCanvasElement) {
    this._canvas = canvas
    this._lastTime = performance.now()

    this.scene = new THREE.Scene()
    this.scene.background = new THREE.Color(0x1a1a2e)

    const w = canvas.clientWidth
    const h = Math.max(canvas.clientHeight, 1)
    this.camera = new THREE.PerspectiveCamera(60, w / h, 0.01, 100)
    this.camera.position.set(5, 3, 5)
    this.camera.lookAt(0, 0, 0)

    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true })
    this.renderer.setSize(w, canvas.clientHeight)
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

    this.controls = new OrbitControls(this.camera, this.renderer.domElement)
    this.controls.enableDamping = true
    this.controls.dampingFactor = 0.1
    this.controls.target.set(0, 0, 0)

    this.cloudGroup = new THREE.Group()
    this.trailGroup = new THREE.Group()
    this.crackGroup = new THREE.Group()
    this.scene.add(this.cloudGroup)
    this.scene.add(this.trailGroup)
    this.scene.add(this.crackGroup)

    this._addLights()
    this.scene.add(new THREE.GridHelper(20, 20, 0x444466, 0x222244))
    this.scene.add(new THREE.AxesHelper(1))

    this._onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      this._keysDown.add(e.key.toLowerCase())
    }
    this._onKeyUp = (e: KeyboardEvent) => {
      this._keysDown.delete(e.key.toLowerCase())
    }
    window.addEventListener('keydown', this._onKeyDown)
    window.addEventListener('keyup', this._onKeyUp)

    this._animationId = requestAnimationFrame(() => this._loop())
  }

  private _addLights(): void {
    this.scene.add(new THREE.AmbientLight(0xffffff, 0.7))
    const d1 = new THREE.DirectionalLight(0xffffff, 0.9)
    d1.position.set(2, 4, 3)
    this.scene.add(d1)
    const d2 = new THREE.DirectionalLight(0xffffff, 0.5)
    d2.position.set(-2, -1, -2)
    this.scene.add(d2)
  }

  private _loop(): void {
    if (this._disposed) return
    const now = performance.now()
    const dt = Math.min((now - this._lastTime) / 1000, 0.1)
    this._lastTime = now
    this._updateWalk(dt)
    this.controls.update()
    this.renderer.render(this.scene, this.camera)
    this._animationId = requestAnimationFrame(() => this._loop())
  }

  private _forward = new THREE.Vector3()
  private _right = new THREE.Vector3()
  private _up = new THREE.Vector3(0, 1, 0)

  private _updateWalk(dt: number): void {
    if (this._keysDown.size === 0) return
    const dist = MOVE_SPEED * dt
    this.camera.getWorldDirection(this._forward)
    this._forward.y = 0
    if (this._forward.lengthSq() < 1e-9) this._forward.set(0, 0, -1)
    this._forward.normalize()
    this._right.crossVectors(this._forward, this._up).normalize()

    if (this._keysDown.has('w')) {
      this.camera.position.addScaledVector(this._forward, dist)
      this.controls.target.addScaledVector(this._forward, dist)
    }
    if (this._keysDown.has('s')) {
      this.camera.position.addScaledVector(this._forward, -dist)
      this.controls.target.addScaledVector(this._forward, -dist)
    }
    if (this._keysDown.has('a')) {
      this.camera.position.addScaledVector(this._right, -dist)
      this.controls.target.addScaledVector(this._right, -dist)
    }
    if (this._keysDown.has('d')) {
      this.camera.position.addScaledVector(this._right, dist)
      this.controls.target.addScaledVector(this._right, dist)
    }
    if (this._keysDown.has('q')) {
      this.camera.position.y -= dist
      this.controls.target.y -= dist
    }
    if (this._keysDown.has('e')) {
      this.camera.position.y += dist
      this.controls.target.y += dist
    }
  }

  resize(width: number, height: number): void {
    if (width <= 0 || height <= 0) return
    this.camera.aspect = width / height
    this.camera.updateProjectionMatrix()
    this.renderer.setSize(width, height)
  }

  resetCamera(): void {
    this.camera.position.set(5, 3, 5)
    this.controls.target.set(0, 0, 0)
    this.controls.update()
  }

  resetScene(): void {
    ;[this.cloudGroup, this.trailGroup, this.crackGroup].forEach((group) => {
      group.traverse((child) => {
        if (child instanceof THREE.Points || child instanceof THREE.Mesh || child instanceof THREE.Line) {
          child.geometry?.dispose()
          if (Array.isArray(child.material)) {
            child.material.forEach((m) => m.dispose())
          } else {
            child.material?.dispose()
          }
        }
      })
      group.clear()
    })
  }

  dispose(): void {
    this._disposed = true
    if (this._animationId !== null) {
      cancelAnimationFrame(this._animationId)
      this._animationId = null
    }
    if (this._onKeyDown) window.removeEventListener('keydown', this._onKeyDown)
    if (this._onKeyUp) window.removeEventListener('keyup', this._onKeyUp)
    this.resetScene()
    this.controls.dispose()
    this.renderer.dispose()
    this.scene.clear()
  }
}
