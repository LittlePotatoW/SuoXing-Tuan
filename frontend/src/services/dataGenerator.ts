// ============================================================
// frontend/src/services/dataGenerator.ts
// 模拟数据生成 — 测试用合成图像、点云、小车轨迹
// ============================================================

let _jpegCanvas: HTMLCanvasElement | null = null

function getJpegCanvas(): HTMLCanvasElement {
  if (!_jpegCanvas) {
    _jpegCanvas = document.createElement('canvas')
    _jpegCanvas.width = 544
    _jpegCanvas.height = 384
  }
  return _jpegCanvas
}

/** 生成 RGB 渐变测试图，返回纯 base64 字符串（不含 data URI 前缀） */
export function makeSyntheticJpegBase64(w = 544, h = 384): string {
  const c = getJpegCanvas()
  if (c.width !== w || c.height !== h) {
    c.width = w
    c.height = h
  }
  const ctx = c.getContext('2d')!
  const imgData = ctx.createImageData(w, h)
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4
      imgData.data[i] = Math.floor(255 * (1 - x / w))       // R
      imgData.data[i + 1] = Math.floor(255 * (x / w))       // G
      imgData.data[i + 2] = Math.floor(255 * (y / h))       // B
      imgData.data[i + 3] = 255
    }
  }
  ctx.putImageData(imgData, 0, 0)
  const dataUrl = c.toDataURL('image/jpeg', 0.85)
  return dataUrl.slice(dataUrl.indexOf(',') + 1)
}

/** 在 (cx, cy, cz) 生成立方体表面点云 + 地面噪点，返回扁平数组 [x0,y0,z0, x1,y1,z1, ...] */
export function makeCubePoints(cx: number, cy: number, cz: number, size = 0.5, n = 300): number[] {
  const pts: number[] = []
  const half = size / 2
  for (let i = 0; i < n; i++) {
    const face = i % 6
    const rx = Math.random() * size - half
    const ry = Math.random() * size - half
    const rz = Math.random() * size - half
    switch (face) {
      case 0: pts.push(cx + rx, cy - half, cz + rz); break
      case 1: pts.push(cx + rx, cy + half, cz + rz); break
      case 2: pts.push(cx - half, cy + ry, cz + rz); break
      case 3: pts.push(cx + half, cy + ry, cz + rz); break
      case 4: pts.push(cx + rx, cy + ry, cz - half); break
      case 5: pts.push(cx + rx, cy + ry, cz + half); break
    }
  }
  // 地面点
  for (let i = 0; i < 50; i++) {
    pts.push(
      cx + (Math.random() - 0.5) * 3,
      (Math.random() - 0.5) * 3,
      cz - half + (Math.random() - 0.5) * 0.04,
    )
  }
  return pts
}

// ── 小车物理模型 ──

export interface CarPose {
  position: { x: number; y: number; z: number }
  rotation: { qw: number; qx: number; qy: number; qz: number }
}

export class Car {
  x = 0
  y = 0
  yaw = 0
  velocity = 0.5
  steering = 0
  wheelBase = 1.5

  constructor(opts?: { velocity?: number; steering?: number; wheelBase?: number }) {
    if (opts?.velocity !== undefined) this.velocity = opts.velocity
    if (opts?.steering !== undefined) this.steering = opts.steering
    if (opts?.wheelBase !== undefined) this.wheelBase = opts.wheelBase
  }

  step(dt: number) {
    if (Math.abs(this.steering) < 1e-6) {
      this.x += this.velocity * Math.cos(this.yaw) * dt
      this.y += this.velocity * Math.sin(this.yaw) * dt
    } else {
      const R = this.wheelBase / Math.tan(this.steering)
      const omega = this.velocity / R
      this.yaw += omega * dt
      this.x += R * (Math.sin(this.yaw) - Math.sin(this.yaw - omega * dt))
      this.y += R * (Math.cos(this.yaw - omega * dt) - Math.cos(this.yaw))
    }
  }

  pose(): CarPose {
    const half = this.yaw / 2
    return {
      position: { x: +this.x.toFixed(4), y: +this.y.toFixed(4), z: 0 },
      rotation: { qw: Math.cos(half), qx: 0, qy: 0, qz: Math.sin(half) },
    }
  }

  reset() {
    this.x = 0; this.y = 0; this.yaw = 0
  }
}

// ── Straight-line trajectory helper ──

export function straightPose(t: number, speed: number): CarPose {
  return {
    position: { x: speed * t, y: 0, z: 0 },
    rotation: { qw: 1, qx: 0, qy: 0, qz: 0 },
  }
}

// ── 数据包生成 ──

const CAMERA_POSE = {
  position: { x: 0, y: 0, z: 1 },
  rotation: { qw: 0.7071, qx: 0, qy: 0.7071, qz: 0 },
}

export function makeLocationData(tsNs: number, car: Car) {
  return {
    timestamp_ns: tsNs,
    camera: [{ camera_pose: CAMERA_POSE }],
    car: {
      kinematics: {
        velocity: car.velocity,
        steering_angle: car.steering,
        wheel_base: car.wheelBase,
      },
    },
  }
}

export function makeSensorFrame(
  frameId: string,
  tsNs: number,
  car: Car,
  imgB64: string,
) {
  const pose = car.pose()
  const pts = makeCubePoints(car.x + 3, 0, 1, 0.5, 300)
  return {
    frame_id: frameId,
    timestamp_ns: tsNs,
    point_cloud: { points: pts, point_count: Math.floor(pts.length / 3) },
    camera_views: [{
      image_data: imgB64,
      width: 544,
      height: 384,
      camera_pose: CAMERA_POSE,
    }],
    car_position: { pose, timestamp_ns: tsNs },
    kinematics: {
      velocity: car.velocity,
      steering_angle: car.steering,
      wheel_base: car.wheelBase,
      timestamp_ns: tsNs,
    },
  }
}

export function makeSensorFrameStraight(frameId: string, tsNs: number, t0: number, speed: number, imgB64: string) {
  const t = (tsNs - t0) / 1e9
  const pose = straightPose(t, speed)
  const x = speed * t
  const pts = makeCubePoints(x + 3, 0, 1, 0.5, 300)
  return {
    frame_id: frameId,
    timestamp_ns: tsNs,
    point_cloud: { points: pts, point_count: Math.floor(pts.length / 3) },
    camera_views: [{
      image_data: imgB64,
      width: 544,
      height: 384,
      camera_pose: CAMERA_POSE,
    }],
    car_position: { pose, timestamp_ns: tsNs },
    kinematics: {
      velocity: speed,
      steering_angle: 0,
      wheel_base: 1.5,
      timestamp_ns: tsNs,
    },
  }
}
