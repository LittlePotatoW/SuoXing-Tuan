# ============================================================
# backend/server/api/routes/report.py
# Report 保存/列举/加载 — 文件夹格式（metadata.json + images/）
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
    """保存报告: 写入 metadata.json (图片已由引擎实时写入 report 目录)"""
    report_dir = REPORT_DIR / body.filename.replace('.json', '')
    report_dir.mkdir(parents=True, exist_ok=True)
    img_dir = report_dir / 'images'
    img_dir.mkdir(exist_ok=True)

    data = body.data
    # 去掉 base64 数据（图已在 report 目录），只保留路径引用
    for det in data.get('defects', []):
        ai = det.pop('annotated_image', None) or det.pop('annotatedImage', None)
        if ai:
            det['image'] = ai  # 已经是 "images/<frame_id>.jpg"

    (report_dir / 'metadata.json').write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    return {"status": "ok", "dir": report_dir.name}


@router.get("/list", response_model=list[ReportListItem])
def list_reports():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    items: list[ReportListItem] = []
    for entry in sorted(REPORT_DIR.iterdir(), reverse=True):
        if entry.is_dir() and (entry / 'metadata.json').exists():
            items.append(ReportListItem(filename=entry.name))
    return items


@router.get("/{name:path}")
def load_report(name: str):
    p = REPORT_DIR / name / 'metadata.json'
    if not p.exists():
        raise HTTPException(404, f"Report {name} 不存在")
    return json.loads(p.read_text(encoding='utf-8'))
