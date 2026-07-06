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
#   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# ============================================================

import logging
import shutil
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image
from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from inference import InferenceEngine, InferenceResponse, DetectionResult
from reconstruction.routes import router as reconstruction_router

# ==================== 日志 ====================

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

# ==================== 全局状态 ====================

engine = InferenceEngine()
MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

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

# ==================== REST API ====================

@app.get("/api/health")
async def health():
    """健康检查 — 前端用此检测后端是否在线"""
    return {
        "status": "ok",
        "model_loaded": engine.loaded,
        "model_name": engine.model_name or "none",
    }


@app.post("/api/inference", response_model=InferenceResponse)
async def inference(image: UploadFile = File(...)):
    """
    上传图片进行推理。
    前端发图片 → 后端推理 → 返回检测结果。
    前端不参与推理计算。
    """
    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(400, "Only image files are accepted")

    if not engine.loaded:
        raise HTTPException(503, "No model loaded. Upload a .pt file via /api/model/load first.")

    try:
        # 读取图片
        contents = await image.read()
        pil_img = Image.open(BytesIO(contents)).convert("RGB")
        img_array = np.array(pil_img)  # (H, W, 3) RGB
        img_array = img_array[:, :, ::-1]  # RGB → BGR

        # 推理
        result = engine.infer(img_array)
        logger.info("Inference: %d detections in %.1fms", len(result.detections), result.inference_time_ms)
        return result

    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        logger.exception("Inference failed")
        raise HTTPException(500, f"Inference failed: {e}")


@app.post("/api/model/load")
async def model_load(model_file: UploadFile = File(...)):
    """
    上传模型文件 → 后端热加载。
    前端拔插式换模型的核心接口。
    支持 .pt / .onnx / .engine
    """
    filename = model_file.filename or "model.pt"
    ext = Path(filename).suffix.lower()
    if ext not in (".pt", ".onnx", ".engine"):
        raise HTTPException(400, f"Unsupported format: {ext}. Use .pt, .onnx, or .engine")

    try:
        # 保存到 models/ 目录
        dest = MODEL_DIR / filename
        with open(dest, "wb") as f:
            shutil.copyfileobj(model_file.file, f)

        logger.info("Model saved: %s (%d bytes)", dest, dest.stat().st_size)

        # 热加载
        engine.load(str(dest))

        return {
            "status": "loaded",
            "model_name": engine.model_name,
            "model_path": engine.model_path,
        }
    except Exception as e:
        logger.exception("Model load failed")
        raise HTTPException(500, f"Model load failed: {e}")


# ==================== WebSocket ====================

ws_clients: list[WebSocket] = []


@app.websocket("/ws/realtime")
async def ws_realtime(ws: WebSocket):
    """
    WebSocket 实时通信。
    前端连接后可接收后端主动推送的检测结果和图像帧。
    """
    await ws.accept()
    ws_clients.append(ws)
    logger.info("WS client connected (%d total)", len(ws_clients))

    await ws.send_json({"type": "status", "message": "Connected to SuoXing-Tuan backend"})

    try:
        while True:
            data = await ws.receive_text()
            import json
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                if msg_type == "switch_model":
                    # 前端请求切换模型（后端已有多个模型时）
                    model_name = msg.get("model_name", "")
                    await ws.send_json({
                        "type": "status",
                        "message": f"Model switch not supported yet. Use POST /api/model/load.",
                    })
                else:
                    await ws.send_json({
                        "type": "status",
                        "message": f"Unknown message type: {msg_type}",
                    })
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        ws_clients.remove(ws)
        logger.info("WS client disconnected (%d total)", len(ws_clients))


# ==================== 启动 ====================

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting SuoXing-Tuan backend...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
