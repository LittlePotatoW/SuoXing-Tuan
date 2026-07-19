# ============================================================
# backend/server/api/routes/report.py
# Report 保存/列举/加载
# ============================================================

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from server.api.schemas.report import ReportSaveRequest, ReportListItem

router = APIRouter(prefix="/api/report", tags=["report"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
REPORT_DIR = PROJECT_ROOT / "Report_Data"


@router.post("/save", status_code=200)
def save_report(body: ReportSaveRequest):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / body.filename).write_text(
        json.dumps(body.data, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    return {"status": "ok", "filename": body.filename}


@router.get("/list", response_model=list[ReportListItem])
def list_reports():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    items: list[ReportListItem] = []
    for entry in sorted(REPORT_DIR.iterdir(), reverse=True):
        if entry.is_file() and entry.suffix == '.json':
            items.append(ReportListItem(filename=entry.name))
    return items


@router.get("/{filename:path}")
def load_report(filename: str):
    p = REPORT_DIR / filename
    if not p.exists():
        raise HTTPException(404, f"Report {filename} 不存在")
    return json.loads(p.read_text(encoding='utf-8'))
