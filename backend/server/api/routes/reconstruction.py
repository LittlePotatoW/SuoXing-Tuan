# ============================================================
# backend/server/api/routes/reconstruction.py
# 重建引擎接口：状态查询、结果获取、WebSocket 推送
#
# 设计与用法:
#   导出 router (APIRouter)
#   导出 _broadcast(payload) — 向所有 WS 客户端广播
#   GET  /status   重建进度查询
#   GET  /result   重建结果获取 (支持 ?since=)
#   POST /reset    重置重建引擎 + 改参数
#   GET  /config   查询引擎配置
#   WS   /ws       重建结果推送
# ============================================================

import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from server.api.schemas.reconstruction import (
    ReconstructionStatusResponse, ReconstructionResultResponse,
    ReconResetRequest, ReconConfigResponse,
)

router = APIRouter(prefix="/api/reconstruction", tags=["reconstruction"])

# WebSocket 连接管理
_ws_clients: list[WebSocket] = []
_ws_lock = asyncio.Lock()


async def _broadcast(payload: dict) -> None:
    """向所有 WebSocket 客户端广播消息"""
    async with _ws_lock:
        clients = list(_ws_clients)
    dead: list[WebSocket] = []
    for ws in clients:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    if dead:
        async with _ws_lock:
            for ws in dead:
                try:
                    _ws_clients.remove(ws)
                except ValueError:
                    pass


@router.websocket("/ws")
async def ws_reconstruction(ws: WebSocket):
    await ws.accept()
    async with _ws_lock:
        _ws_clients.append(ws)
    try:
        while True:
            await ws.receive_text()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        async with _ws_lock:
            try:
                _ws_clients.remove(ws)
            except ValueError:
                pass


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


# ============================================================
# 重建引擎管理
# ============================================================

@router.post("/reset", status_code=200)
def reset_reconstruction(body: ReconResetRequest):
    """重置重建引擎，可选改参数"""
    from server.engine import ReconstructionEngine, set_report_name, clear_report_name
    clear_report_name()
    ReconstructionEngine.stop()
    eng = ReconstructionEngine.create(
        mode=body.mode,
        frame_threshold=body.frame_threshold,
        voxel_size=body.voxel_size,
        method=body.method,
        yolo_enabled=(body.yolo_enabled
                      if body.yolo_enabled is not None else True),
    )
    eng._cumulative_defects = []
    if body.report_name:
        set_report_name(body.report_name)
    engine = ReconstructionEngine.create()
    return {"status": "ok", "mode": engine._mode}


@router.get("/config", response_model=ReconConfigResponse)
def get_recon_config() -> ReconConfigResponse:
    """查询重建引擎当前配置和状态"""
    from server.engine import ReconstructionEngine
    engine = ReconstructionEngine.create()
    cfg = engine.get_config()
    return ReconConfigResponse(**cfg)
