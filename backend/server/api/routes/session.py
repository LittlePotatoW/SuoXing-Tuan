# ============================================================
# backend/server/api/routes/session.py
# Session 保存/列举/加载 + 帧文件服务
#
# 自动保存模式（后端驱动）:
#   POST /start   前端发信号 → 引擎自动逐帧写盘
#   POST /stop    前端发信号 → 引擎写最终 manifest
# 旧接口保留兼容:
#   POST /create  /frame  /save
# ============================================================

import base64
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from server.api.schemas.session import (
    SessionCreateRequest, SessionFrameRequest,
    SessionSaveRequest, SessionListItem,
)

router = APIRouter(prefix="/api/session", tags=["session"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
SESSION_DIR = PROJECT_ROOT / "Session_Data"


@router.post("/start", status_code=200)
def start_session(body: dict = {}):
    """前端信号：开始 Session → 后端引擎自动逐帧写盘"""
    from datetime import datetime
    task = body.get('task_name', '') if body else ''
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    name = f"session_{task}_{ts}" if task else f"session_{ts}"
    from server.engine.engine import set_session_name
    set_session_name(name)
    return {"status": "ok", "name": name}


@router.post("/stop", status_code=200)
def stop_session():
    """前端信号：停止 Session → 写最终 manifest"""
    from server.engine.engine import finalize_session
    finalize_session()
    return {"status": "ok"}


@router.post("/create", status_code=200)
def create_session(body: SessionCreateRequest):
    """创建 session 目录和初始 manifest"""
    session_path = SESSION_DIR / body.name
    frames_path = session_path / "frames"
    frames_path.mkdir(parents=True, exist_ok=True)

    manifest = {
        "version": 1,
        "start_time": body.start_time,
        "frame_count": 0,
        "telemetry_interval_ms": body.telemetry_interval_ms,
        "telemetry": [],
        "frames": [],
    }
    (session_path / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    return {"status": "ok", "name": body.name}


@router.post("/frames", status_code=200)
def save_frames(body: dict):
    """批次写盘：一次请求写入多帧"""
    session_name = body.get('session_name', '')
    frames = body.get('frames', [])
    if not session_name or not frames:
        raise HTTPException(400, "缺少 session_name 或 frames")
    session_path = SESSION_DIR / session_name
    frames_path = session_path / "frames"
    frames_path.mkdir(parents=True, exist_ok=True)
    for f in frames:
        img_path = frames_path / f.get('image_name', '')
        dep_path = frames_path / f.get('depth_name', '')
        img_path.write_bytes(base64.b64decode(f.get('image_data', '')))
        dep_path.write_bytes(base64.b64decode(f.get('depth_data', '')))
    return {"status": "ok", "count": len(frames)}


@router.post("/frame", status_code=200)
def save_frame(body: SessionFrameRequest):
    """逐帧写盘：image JPEG + depth PNG"""
    session_path = SESSION_DIR / body.session_name
    if not session_path.exists():
        raise HTTPException(404, f"Session {body.session_name} 不存在，请先 POST /create")

    frames_path = session_path / "frames"
    frames_path.mkdir(parents=True, exist_ok=True)

    img_path = frames_path / body.image_name
    depth_path = frames_path / body.depth_name

    img_path.write_bytes(base64.b64decode(body.image_data))
    depth_path.write_bytes(base64.b64decode(body.depth_data))

    return {"status": "ok", "frame_id": body.frame_id}


@router.post("/save", status_code=200)
def save_session(body: SessionSaveRequest):
    """更新 manifest.json（帧文件已通过 /frame 写入）"""
    session_path = SESSION_DIR / body.name
    if not session_path.exists():
        session_path.mkdir(parents=True, exist_ok=True)
        (session_path / "frames").mkdir(exist_ok=True)

    (session_path / "manifest.json").write_text(
        json.dumps(body.manifest, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    return {"status": "ok", "name": body.name, "frame_count": body.manifest.get("frame_count", 0)}


@router.get("/list", response_model=list[SessionListItem])
def list_sessions():
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    items: list[SessionListItem] = []
    for entry in sorted(SESSION_DIR.iterdir(), reverse=True):
        if entry.is_dir() and (entry / "manifest.json").exists():
            try:
                m = json.loads((entry / "manifest.json").read_text(encoding="utf-8"))
                fc = m.get("frame_count", 0)
            except Exception:
                fc = 0
            items.append(SessionListItem(name=entry.name, frame_count=fc))
    return items


@router.get("/{name}")
def load_session(name: str):
    p = SESSION_DIR / name / "manifest.json"
    if not p.exists():
        raise HTTPException(404, f"Session {name} 不存在")
    return json.loads(p.read_text(encoding="utf-8"))


@router.get("/files/{session_name}/{file_path:path}")
def get_session_file(session_name: str, file_path: str):
    p = SESSION_DIR / session_name / file_path
    if not p.exists():
        raise HTTPException(404, f"文件 {file_path} 不存在")
    return FileResponse(str(p))
