# ============================================================
# backend/server/api/routes/session.py
# Session 保存/列举/加载 + 帧文件服务
# ============================================================

import base64
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from server.api.schemas.session import (
    SessionSaveRequest, SessionListItem,
)

router = APIRouter(prefix="/api/session", tags=["session"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
SESSION_DIR = PROJECT_ROOT / "Session_Data"


@router.post("/save", status_code=200)
def save_session(body: SessionSaveRequest):
    session_path = SESSION_DIR / body.name
    frames_path = session_path / "frames"
    frames_path.mkdir(parents=True, exist_ok=True)

    manifest_path = session_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(body.manifest, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    for f in body.frames:
        fp = session_path / f.filename
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_bytes(base64.b64decode(f.data))

    return {"status": "ok", "name": body.name, "frame_count": len(body.frames)}


@router.get("/list", response_model=list[SessionListItem])
def list_sessions():
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    items: list[SessionListItem] = []
    for entry in sorted(SESSION_DIR.iterdir(), reverse=True):
        if entry.is_dir() and (entry / "manifest.json").exists():
            try:
                m = json.loads((entry / "manifest.json").read_text(encoding='utf-8'))
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
    return json.loads(p.read_text(encoding='utf-8'))


@router.get("/files/{session_name}/{file_path:path}")
def get_session_file(session_name: str, file_path: str):
    p = SESSION_DIR / session_name / file_path
    if not p.exists():
        raise HTTPException(404, f"文件 {file_path} 不存在")
    return FileResponse(str(p))
