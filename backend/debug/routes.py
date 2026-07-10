# ============================================================
# backend/debug/routes.py
# 调试用数据存取 — data_captures/ 文件夹的读写接口
# ============================================================

import json
import os
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/api/debug")

# data_captures/ 在项目根目录
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data_captures"


def _session_dir(name: str) -> Path:
    """安全校验 session name，避免路径穿越"""
    p = (DATA_DIR / name).resolve()
    if not str(p).startswith(str(DATA_DIR.resolve())):
        raise HTTPException(400, "Invalid session name")
    return p


def _next_index(dir_path: Path) -> int:
    """返回下一个可用序号 (1-based)"""
    if not dir_path.exists():
        return 1
    files = [f for f in os.listdir(str(dir_path)) if f.endswith(".json")]
    if not files:
        return 1
    nums = []
    for f in files:
        try:
            nums.append(int(Path(f).stem))
        except ValueError:
            pass
    return max(nums) + 1 if nums else 1


# ── 保存 ──

@router.post("/save/location")
async def save_location(req: Request):
    session = req.query_params.get("session", "default")
    body = await req.json()
    d = _session_dir(session) / "location"
    d.mkdir(parents=True, exist_ok=True)
    idx = _next_index(d)
    (d / f"{idx:05d}.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "file": f"{idx:05d}.json"}


@router.post("/save/sensor")
async def save_sensor(req: Request):
    session = req.query_params.get("session", "default")
    body = await req.json()
    d = _session_dir(session) / "sensor"
    d.mkdir(parents=True, exist_ok=True)
    idx = _next_index(d)
    (d / f"{idx:05d}.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "file": f"{idx:05d}.json"}


@router.post("/save/fusion")
async def save_fusion(req: Request):
    session = req.query_params.get("session", "default")
    body = await req.json()
    d = _session_dir(session) / "fusion"
    d.mkdir(parents=True, exist_ok=True)
    idx = _next_index(d)
    (d / f"{idx:05d}.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "file": f"{idx:05d}.json"}


# ── 读取 ──

@router.get("/sessions")
async def list_sessions():
    if not DATA_DIR.exists():
        return {"sessions": []}
    sessions = [d.name for d in DATA_DIR.iterdir() if d.is_dir()]
    return {"sessions": sorted(sessions)}


@router.get("/sessions/{name}/info")
async def session_info(name: str):
    d = _session_dir(name)
    if not d.exists():
        return {"location": 0, "sensor": 0, "fusion": 0}
    counts = {}
    for sub in ("location", "sensor", "fusion"):
        sd = d / sub
        counts[sub] = len([f for f in os.listdir(str(sd)) if f.endswith(".json")]) if sd.exists() else 0
    return counts


@router.get("/sessions/{name}/location")
async def get_locations(name: str):
    d = _session_dir(name) / "location"
    if not d.exists():
        return {"frames": []}
    files = sorted([f for f in os.listdir(str(d)) if f.endswith(".json")])
    frames = []
    for fname in files:
        try:
            frames.append(json.loads((d / fname).read_text(encoding="utf-8")))
        except Exception:
            pass
    return {"frames": frames}


@router.get("/sessions/{name}/sensor")
async def get_sensors(name: str):
    d = _session_dir(name) / "sensor"
    if not d.exists():
        return {"frames": []}
    files = sorted([f for f in os.listdir(str(d)) if f.endswith(".json")])
    frames = []
    for fname in files:
        try:
            frames.append(json.loads((d / fname).read_text(encoding="utf-8")))
        except Exception:
            pass
    return {"frames": frames}


@router.get("/sessions/{name}/fusion")
async def get_fusions(name: str):
    d = _session_dir(name) / "fusion"
    if not d.exists():
        return {"frames": []}
    files = sorted([f for f in os.listdir(str(d)) if f.endswith(".json")])
    frames = []
    for fname in files:
        try:
            frames.append(json.loads((d / fname).read_text(encoding="utf-8")))
        except Exception:
            pass
    return {"frames": frames}
