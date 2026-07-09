# ============================================================
# backend/main.py
# SuoXing-Tuan 后端服务 — FastAPI 应用入口
#
# 负责:
#   1. 接收前端请求 (REST API)
#   2. 运行 AI 推理 (YOLO 等)
#   3. 实时推送 (WebSocket)
#   4. 模型热加载 (拔插式换 .pt 文件)
#
# 用法:
#   python main.py
#   uvicorn main:app --host 127.0.0.1 --port 8000
# ============================================================

import os
import json
import asyncio
import logging
import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import numpy as np
from PIL import Image
from fastapi import FastAPI, Request, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from inference.engine import InferenceEngine
from inference.schemas import InferenceResponse, DetectionResult
from reconstruction.routes import router as reconstruction_router
from state_estimation.router import router as preprocessing_router
from realtime.fusion_router import router as realtime_router, set_inference_engine

# ==================== 配置 ====================

LOG_LEVEL = os.getenv("SX_LOG_LEVEL", "INFO")
HOST = os.getenv("SX_HOST", "127.0.0.1")
PORT = int(os.getenv("SX_PORT", "8000"))
MAX_IMAGE_MB = int(os.getenv("SX_MAX_IMAGE_MB", "50"))
MAX_MODEL_MB = int(os.getenv("SX_MAX_MODEL_MB", "200"))
DEFAULT_MODEL = os.getenv("SX_DEFAULT_MODEL", "crack-detector.pt")

# ==================== 日志 ====================

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

# ==================== 全局状态 ====================

engine = InferenceEngine()
MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

# 启动时自动加载默认模型
_default_model = MODEL_DIR / DEFAULT_MODEL
if _default_model.exists():
    engine.load(str(_default_model))
    logger.info("Auto-loaded default model: %s", _default_model.name)

# ==================== FastAPI 应用 ====================

app = FastAPI(
    title="SuoXing-Tuan Backend",
    version="0.1.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reconstruction_router)
app.include_router(preprocessing_router)
app.include_router(realtime_router)
set_inference_engine(engine)

# ==================== 请求追踪中间件 ====================

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4())[:8])
    logger.debug("[%s] %s %s", request_id, request.method, request.url.path)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# ==================== REST API ====================

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "model_loaded": engine.loaded,
        "model_name": engine.model_name or "none",
    }


@app.post("/api/inference", response_model=InferenceResponse)
async def inference(image: UploadFile = File(...)):
    if not engine.loaded:
        raise HTTPException(503, "No model loaded")

    # 读取图片（限制大小）
    contents = b""
    chunk_size = 1024 * 1024
    max_bytes = MAX_IMAGE_MB * 1024 * 1024
    while True:
        chunk = await image.read(chunk_size)
        if not chunk:
            break
        contents += chunk
        if len(contents) > max_bytes:
            raise HTTPException(413, f"Image too large (max {MAX_IMAGE_MB} MB)")

    try:
        pil_img = Image.open(BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(400, "Invalid or corrupt image file")

    img_array = np.array(pil_img)  # (H, W, 3) RGB
    h, w = img_array.shape[:2]
    if h < 16 or w < 16 or h > 8192 or w > 8192:
        raise HTTPException(400, f"Image dimensions {w}x{h} out of range [16, 8192]")

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, engine.infer, img_array)
        logger.info("[inference] %d detections in %.1fms", len(result.detections), result.inference_time_ms)
        return result
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        logger.exception("Inference failed")
        raise HTTPException(500, "Inference internal error")


@app.post("/api/model/load")
async def model_load(model_file: UploadFile = File(...)):
    raw_name = model_file.filename or "model.pt"
    filename = Path(raw_name).name  # 防止路径穿越
    ext = Path(filename).suffix.lower()
    if ext not in (".pt", ".onnx", ".engine"):
        raise HTTPException(400, f"Unsupported format: {ext}. Use .pt, .onnx, or .engine")

    # 分块写入 + 大小限制 + 原子写入（先写临时文件再 rename）
    try:
        dest = MODEL_DIR / filename
        max_bytes = MAX_MODEL_MB * 1024 * 1024
        total = 0
        tmp = tempfile.NamedTemporaryFile(dir=MODEL_DIR, delete=False, suffix=".tmp")
        try:
            while chunk := await model_file.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    tmp.close()
                    Path(tmp.name).unlink(missing_ok=True)
                    raise HTTPException(413, f"Model too large (max {MAX_MODEL_MB} MB)")
                tmp.write(chunk)
            tmp.close()
            os.replace(tmp.name, dest)  # 原子 rename
        except Exception:
            Path(tmp.name).unlink(missing_ok=True)
            raise

        logger.info("Model saved: %s (%d bytes)", dest, dest.stat().st_size)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, engine.load, str(dest))

        return {
            "status": "loaded",
            "model_name": engine.model_name,
            "model_path": engine.model_path,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Model load failed")
        if dest.exists():
            dest.unlink(missing_ok=True)
        raise HTTPException(500, f"Model load failed: {e}")


# ==================== WebSocket ====================

ws_clients: list[WebSocket] = []
ws_lock = asyncio.Lock()


@app.websocket("/ws/realtime")
async def ws_realtime(ws: WebSocket):
    await ws.accept()

    async with ws_lock:
        ws_clients.append(ws)
        total = len(ws_clients)
    logger.info("WS client connected (%d total)", total)

    await ws.send_json({"type": "status", "message": "Connected to SuoXing-Tuan backend"})

    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                if msg_type == "switch_model":
                    await ws.send_json({
                        "type": "status",
                        "message": "Model switch not supported yet. Use POST /api/model/load.",
                    })
                else:
                    await ws.send_json({
                        "type": "status",
                        "message": f"Unknown message type: {msg_type}",
                    })
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        async with ws_lock:
            if ws in ws_clients:
                ws_clients.remove(ws)
            total = len(ws_clients)
        logger.info("WS client disconnected (%d total)", total)


# ==================== 启动 ====================

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting SuoXing-Tuan backend on %s:%s", HOST, PORT)
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
