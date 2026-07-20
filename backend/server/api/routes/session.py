# ============================================================
# backend/server/api/routes/session.py
# Session 保存/列举/加载 + 帧文件服务
#
# 增量保存模式（参照 Report）:
#   POST /create  创建 session 目录 + 初始 manifest
#   POST /frame   逐帧写盘 (image.jpg + depth.png)
#   POST /save    更新 manifest (帧文件已由 /frame 写入)
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
