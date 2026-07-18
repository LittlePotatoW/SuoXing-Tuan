# ============================================================
# backend/server/api/routes/reconstruction.py
# 重建引擎接口：状态查询、结果获取
#
# 设计与用法:
#   导出 router (APIRouter)
#   GET /status  重建进度查询
#   GET /result  重建结果获取 (支持 ?since=)
# ============================================================

from fastapi import APIRouter, Query

from server.api.schemas.reconstruction import (
    ReconstructionStatusResponse, ReconstructionResultResponse,
)

router = APIRouter(prefix="/api/reconstruction", tags=["reconstruction"])


@router.get("/status", response_model=ReconstructionStatusResponse)
def get_status() -> ReconstructionStatusResponse:
    from server.engine import ReconstructionEngine
    engine = ReconstructionEngine.create()
    s = engine.get_status()
    return ReconstructionStatusResponse(
        status=s["status"],
        frame_count=s["frame_count"],
        frame_threshold=s["frame_threshold"],
        last_result_timestamp=s["last_result_timestamp"],
    )


@router.get("/result", response_model=ReconstructionResultResponse)
def get_result(since: float | None = Query(None,
              description="Unix 时间戳, 只返回该时间之后的新结果")):
    from server.engine import ReconstructionEngine
    engine = ReconstructionEngine.create()
    r = engine.get_result(since)
    if r is None:
        return ReconstructionResultResponse(
            timestamp=0.0,
            point_cloud_url="",
            detections=[],
        )
    return ReconstructionResultResponse(
        timestamp=r["timestamp"],
        point_cloud_url=r["point_cloud_url"],
        detections=r["detections"],
    )
