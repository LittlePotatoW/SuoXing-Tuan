# ============================================================
# test_end/simulator.py
# 小车数据模拟器 — 独立于后端，可发送 location/detection 数据包
#
# 用法:
#   cd test_end && python simulator.py
#   浏览器打开 http://localhost:9000
# ============================================================

import asyncio
import json
import math
import time
import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simulator")

# ── 尝试导入 fastapi/uvicorn ──
try:
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse
    import uvicorn
except ImportError:
    logger.error("请安装 fastapi 和 uvicorn: pip install fastapi uvicorn pillow numpy")
    raise

app = FastAPI(title="小车数据模拟器")

# ============================================================
#  小车物理模型
# ============================================================


class Car:
    def __init__(self):
        self.x: float = 0.0
        self.y: float = 0.0
        self.yaw: float = 0.0
        self.velocity: float = 0.5
        self.steering: float = 0.0
        self.wheel_base: float = 1.5
        self.last_ts: int = 0
        self.path: list[tuple[float, float]] = [(0.0, 0.0)]

    def step(self, dt: float) -> dict:
        if abs(self.steering) < 1e-6:
            self.x += self.velocity * math.cos(self.yaw) * dt
            self.y += self.velocity * math.sin(self.yaw) * dt
        else:
            turn_radius = self.wheel_base / math.tan(self.steering)
            omega = self.velocity / turn_radius
            self.yaw += omega * dt
            self.x += turn_radius * (math.sin(self.yaw) - math.sin(self.yaw - omega * dt))
            self.y += turn_radius * (math.cos(self.yaw - omega * dt) - math.cos(self.yaw))
        self.path.append((self.x, self.y))
        return self.get_pose()

    def get_pose(self) -> dict:
        half = self.yaw / 2.0
        return {
            "position": {"x": round(self.x, 4), "y": round(self.y, 4), "z": 0.0},
            "rotation": {"qw": math.cos(half), "qx": 0.0, "qy": 0.0, "qz": math.sin(half)},
        }

    def reset(self):
        self.x = self.y = self.yaw = 0.0
        self.path = [(0.0, 0.0)]


car = Car()

# ============================================================
#  数据包生成
# ============================================================


def make_location_data(ts_ns: int) -> dict:
    return {
        "timestamp_ns": ts_ns,
        "camera": [{
            "camera_pose": {
                "position": {"x": 0.0, "y": 0.0, "z": 1.0},
                "rotation": {"qw": 0.7071, "qx": 0.0, "qy": 0.7071, "qz": 0.0},
            }
        }],
        "car": {
            "kinematics": {
                "velocity": car.velocity,
                "steering_angle": car.steering,
                "wheel_base": car.wheel_base,
            }
        },
    }


def make_synthetic_jpeg(w=544, h=384) -> bytes:
    """生成彩色测试图"""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            img[y, x] = [
                int(255 * (1 - x / w)),
                int(255 * (x / w)),
                int(255 * (y / h)),
            ]
    buf = BytesIO()
    Image.fromarray(img).save(buf, format='JPEG', quality=85)
    return buf.getvalue()


def make_cube_points(cx, cy, cz, size=0.4, n=300) -> list[float]:
    """合成立方体点云"""
    import random
    pts = []
    half = size / 2
    for _ in range(n):
        face = random.randint(0, 5)
        if face == 0:
            p = (cx + random.uniform(-half, half), cy - half, cz + random.uniform(-half, half))
        elif face == 1:
            p = (cx + random.uniform(-half, half), cy + half, cz + random.uniform(-half, half))
        elif face == 2:
            p = (cx - half, cy + random.uniform(-half, half), cz + random.uniform(-half, half))
        elif face == 3:
            p = (cx + half, cy + random.uniform(-half, half), cz + random.uniform(-half, half))
        elif face == 4:
            p = (cx + random.uniform(-half, half), cy + random.uniform(-half, half), cz - half)
        else:
            p = (cx + random.uniform(-half, half), cy + random.uniform(-half, half), cz + half)
        pts.extend(p)
    return pts


def make_detection_data(frame_id: str, ts_ns: int) -> dict:
    pose = car.get_pose()
    jpeg = make_synthetic_jpeg()
    b64 = base64.b64encode(jpeg).decode()
    pts = make_cube_points(cx=car.x + 3.0, cy=0.0, cz=1.5)
    return {
        "frame_id": frame_id,
        "timestamp_ns": ts_ns,
        "point_cloud": {"points": pts, "point_count": len(pts) // 3},
        "car_position": {
            "pose": pose,
            "timestamp_ns": ts_ns,
        },
        "camera_views": [{
            "image_data": b64,
            "width": 544,
            "height": 384,
            "camera_pose": {
                "position": {"x": 0.0, "y": 0.0, "z": 1.0},
                "rotation": {"qw": 0.7071, "qx": 0.0, "qy": 0.7071, "qz": 0.0},
            }
        }],
    }


# ============================================================
#  HTML 页面 (内嵌)
# ============================================================

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>小车数据模拟器</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:monospace;background:#1a1a1a;color:#ccc;display:flex;height:100vh}
.panel{background:#252525;padding:16px;overflow-y:auto}
.left{width:320px;border-right:1px solid #444}
.right{flex:1;position:relative}
canvas{display:block}
h3{color:#4FC3F7;margin-bottom:12px;font-size:14px}
label{display:block;font-size:12px;color:#aaa;margin-bottom:4px}
input,select{width:100%;padding:6px 8px;background:#1a1a1a;color:#ccc;border:1px solid #444;font-size:12px;margin-bottom:10px}
.row{display:flex;gap:8px}
.row>*{flex:1}
button{padding:8px 0;border:none;cursor:pointer;font-size:12px;font-weight:bold;color:#fff;border-radius:3px;width:100%;margin-bottom:6px}
.btn-loc{background:#1976D2}.btn-det{background:#388E3C}
.btn-stream{background:#E65100}.btn-stop{background:#C62828}.btn-reset{background:#555}
.btn-stream.on{background:#2E7D32}
.status{font-size:11px;color:#888;margin-top:8px;max-height:200px;overflow-y:auto}
.status div{padding:2px 0;border-bottom:1px solid #333}
.backend-url{font-size:11px;color:#666;margin-bottom:8px}
.stat-row{display:flex;justify-content:space-between;font-size:12px;padding:4px 0;color:#aaa}
.stat-row span:last-child{color:#4FC3F7}
</style>
</head>
<body>
<div class="panel left">
  <h3>小车数据模拟器</h3>
  <div class="backend-url">后端: <span id="backendLabel">检测中...</span></div>

  <div class="stat-row"><span>位置 X</span><span id="carX">0.00</span></div>
  <div class="stat-row"><span>位置 Y</span><span id="carY">0.00</span></div>
  <div class="stat-row"><span>朝向</span><span id="carYaw">0.0&deg;</span></div>
  <div class="stat-row"><span>速度</span><span id="carVel">0.5 m/s</span></div>
  <div class="stat-row"><span>location 已发</span><span id="locCount">0</span></div>
  <div class="stat-row"><span>detection 已发</span><span id="detCount">0</span></div>

  <label>速度 (m/s)</label>
  <input type="range" id="velSlider" min="0" max="2" step="0.1" value="0.5" />
  <label>转向角 (rad)</label>
  <input type="range" id="steerSlider" min="-0.5" max="0.5" step="0.01" value="0" />

  <div class="row">
    <button class="btn-loc" onclick="sendLocation()">发送 location</button>
    <button class="btn-det" onclick="sendDetection()">发送 detection</button>
  </div>

  <button class="btn-stream" id="btnStream" onclick="toggleStream()">持续发送</button>
  <button class="btn-reset" onclick="resetAll()">重置小车</button>

  <div class="status" id="statusBox"></div>
</div>

<div class="panel right">
  <canvas id="canvas"></canvas>
</div>

<script>
const BACKEND = 'http://127.0.0.1:8000'
let streaming = false, streamLocId = null, streamDetId = null
let locCount = 0, detCount = 0, frameIdx = 0
let carX = 0, carY = 0, carYaw = 0
let simTimeNs = 1_000_000_000  // 模拟时间 (ns), 避免 Date.now() 精度溢出

// Canvas
const canvas = document.getElementById('canvas')
const ctx = canvas.getContext('2d')
const path = [[0,0]]

function resize() { canvas.width = canvas.parentElement.clientWidth; canvas.height = canvas.parentElement.clientHeight; draw() }
window.addEventListener('resize', resize)
resize()

function draw() {
  ctx.fillStyle = '#1a1a1a'; ctx.fillRect(0,0,canvas.width,canvas.height)
  const cx = canvas.width/2, cy = canvas.height/2, scale = 80
  // Grid
  ctx.strokeStyle='#333'; ctx.lineWidth=0.5
  for (let x=cx%scale;x<canvas.width;x+=scale){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,canvas.height);ctx.stroke()}
  for (let y=cy%scale;y<canvas.height;y+=scale){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(canvas.width,y);ctx.stroke()}
  // Path
  if(path.length>1){ctx.strokeStyle='#4FC3F7';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(cx+path[0][0]*scale,cy-path[0][1]*scale);for(let i=1;i<path.length;i++)ctx.lineTo(cx+path[i][0]*scale,cy-path[i][1]*scale);ctx.stroke()}
  // Car
  const px=cx+carX*scale, py=cy-carY*scale
  ctx.save();ctx.translate(px,py);ctx.rotate(-carYaw)
  ctx.fillStyle='#FF5722';ctx.fillRect(-8,-5,16,10)
  ctx.fillStyle='#FFF';ctx.fillRect(6,-2,4,4)
  ctx.restore()
}

function log(msg) {
  const el = document.getElementById('statusBox')
  el.innerHTML = '<div>'+new Date().toLocaleTimeString()+' '+msg+'</div>' + el.innerHTML
  if(el.children.length>50) el.removeChild(el.lastChild)
}

async function sendLocation() {
  const vel = parseFloat(document.getElementById('velSlider').value)
  const steer = parseFloat(document.getElementById('steerSlider').value)
  simTimeNs += 200_000_000
  // 格式匹配 /api/preprocessing/kinematics 端点 (顶层字段)
  const body = {velocity:vel,steering_angle:steer,wheel_base:1.5,timestamp_ns:simTimeNs}
  try{
    const r=await fetch(BACKEND+'/api/preprocessing/kinematics',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
    const d=await r.json()
    if(d.x!==undefined){carX=d.x;carY=d.y;carYaw=d.yaw}
    path.push([carX,carY])
    locCount++
    updateStats()
    draw()
    log('location &check; x='+carX.toFixed(2)+' y='+carY.toFixed(2))
  }catch(e){log('location &#10007; '+e.message)}
}

async function sendDetection() {
  simTimeNs += 500_000_000; frameIdx++  // +500ms in ns
  const r=await fetch(BACKEND+'/api/reconstruction/frame',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({frame_id:'sim_'+frameIdx,timestamp_ns:simTimeNs,point_cloud:{points:genPoints(carX+3,0,1.5,0.4),point_count:300},car_position:{pose:{position:{x:carX,y:carY,z:0},rotation:{qw:Math.cos(carYaw/2),qx:0,qy:0,qz:Math.sin(carYaw/2)}},timestamp_ns:simTimeNs},camera_views:[{image_data:'__JPEG_B64__',width:544,height:384,camera_pose:{position:{x:0,y:0,z:1},rotation:{qw:0.7071,qx:0,qy:0.7071,qz:0}}}]})})
  try{
    const d=await r.json()
    detCount++
    updateStats()
    log('detection &check; rebuild='+d.rebuild_triggered+' yolo='+(d.yolo_detections||0))
  }catch(e){log('detection &#10007; '+e.message)}
}

function genPoints(cx,cy,cz,s){const pts=[],h=s/2;for(let i=0;i<300;i++){const f=Math.floor(Math.random()*6);const rx=Math.random()*s-h,ry=Math.random()*s-h,rz=Math.random()*s-h;if(f===0)pts.push(cx+rx,cy-h,cz+rz);else if(f===1)pts.push(cx+rx,cy+h,cz+rz);else if(f===2)pts.push(cx-h,cy+ry,cz+rz);else if(f===3)pts.push(cx+h,cy+ry,cz+rz);else if(f===4)pts.push(cx+rx,cy+ry,cz-h);else pts.push(cx+rx,cy+ry,cz+h)}return pts}

async function toggleStream() {
  streaming=!streaming
  const btn=document.getElementById('btnStream')
  if(streaming){btn.textContent='停止发送';btn.classList.add('on');runStream()}
  else{btn.textContent='持续发送';btn.classList.remove('on');stopStream()}
}

function stopStream() {
  if(streamLocId){clearInterval(streamLocId);streamLocId=null}
  if(streamDetId){clearInterval(streamDetId);streamDetId=null}
}

async function runStream() {
  if(!streaming)return
  sendLocation(); sendDetection()
  streamLocId=setInterval(sendLocation,200)
  streamDetId=setInterval(sendDetection,1000)
}

async function resetAll() {
  streaming=false
  const btn=document.getElementById('btnStream');btn.textContent='持续发送';btn.classList.remove('on')
  stopStream()
  try{await fetch(BACKEND+'/api/realtime/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({yolo:true,reconstruction:true})})}catch(e){}
  locCount=detCount=frameIdx=0;simTimeNs=1_000_000_000;carX=carY=carYaw=0;path.length=1;path[0]=[0,0]
  updateStats();draw()
  log('reset')
}

function updateStats() {
  document.getElementById('carX').textContent=carX.toFixed(2)
  document.getElementById('carY').textContent=carY.toFixed(2)
  document.getElementById('carYaw').textContent=(carYaw*180/Math.PI).toFixed(1)+'°'
  document.getElementById('carVel').textContent=document.getElementById('velSlider').value+' m/s'
  document.getElementById('locCount').textContent=locCount
  document.getElementById('detCount').textContent=detCount
}

// Check backend
async function checkBackend() {
  try{const r=await fetch(BACKEND+'/api/health');const d=await r.json();document.getElementById('backendLabel').textContent='✅ '+d.model_name||'ok'}catch(e){document.getElementById('backendLabel').textContent='❌ 后端未启动'}}
checkBackend();setInterval(checkBackend,5000)
resize()
</script>
</body>
</html>"""

# 预生成 JPEG
_JPEG_B64 = base64.b64encode(make_synthetic_jpeg()).decode()
HTML = HTML.replace("__JPEG_B64__", _JPEG_B64)


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


if __name__ == "__main__":
    print("=" * 50)
    print("  小车数据模拟器")
    print("  浏览器打开: http://localhost:9000")
    print("=" * 50)
    uvicorn.run(app, host="127.0.0.1", port=9000, log_level="warning")
