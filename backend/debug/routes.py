# ============================================================
# backend/debug/routes.py
# 调试工具 API — 保存/回放 session 数据
# ============================================================

import json
import os
from pathlib import Path

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/debug", tags=["debug"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data_captures"


def _session_dir(name: str) -> Path:
    return DATA_DIR / name


def _next_index(d: Path) -> int:
    existing = [f.stem for f in d.glob("*.json")]
    nums = []
    for n in existing:
        try:
            nums.append(int(n))
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
async def get_locations(name: str, offset: int = 0, limit: int = 0):
    d = _session_dir(name) / "location"
    if not d.exists():
        return {"frames": [], "total": 0}
    files = sorted([f for f in os.listdir(str(d)) if f.endswith(".json")])
    total = len(files)
    if limit > 0:
        files = files[offset:offset + limit]
    frames = []
    for fname in files:
        try:
            frames.append(json.loads((d / fname).read_text(encoding="utf-8")))
        except Exception:
            pass
    return {"frames": frames, "total": total}


@router.get("/sessions/{name}/sensor")
async def get_sensors(name: str, offset: int = 0, limit: int = 0):
    d = _session_dir(name) / "sensor"
    if not d.exists():
        return {"frames": [], "total": 0}
    files = sorted([f for f in os.listdir(str(d)) if f.endswith(".json")])
    total = len(files)
    if limit > 0:
        files = files[offset:offset + limit]
    frames = []
    for fname in files:
        try:
            frames.append(json.loads((d / fname).read_text(encoding="utf-8")))
        except Exception:
            pass
    return {"frames": frames, "total": total}


@router.get("/sessions/{name}/fusion")
async def get_fusions(name: str, offset: int = 0, limit: int = 0):
    d = _session_dir(name) / "fusion"
    if not d.exists():
        return {"frames": [], "total": 0}
    files = sorted([f for f in os.listdir(str(d)) if f.endswith(".json")])
    total = len(files)
    if limit > 0:
        files = files[offset:offset + limit]
    frames = []
    for fname in files:
        try:
            frames.append(json.loads((d / fname).read_text(encoding="utf-8")))
        except Exception:
            pass
    return {"frames": frames, "total": total}
