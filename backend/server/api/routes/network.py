# ============================================================
# backend/server/api/routes/network.py
# 网络工具接口：本机 IP + 局域网设备扫描
#
# 设计与用法:
#   GET  /api/network/local-ip  → {"ip": "10.99.147.69"}
#   POST /api/network/scan      → {"devices": [...], "subnet": "10.99.147"}
# ============================================================

import asyncio
import socket

import websockets
from fastapi import APIRouter

router = APIRouter(prefix="/api/network", tags=["network"])


def _get_lan_ip() -> str:
    """获取本机局域网 IPv4 地址"""
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if not ip.startswith("127."):
            return ip
    except Exception:
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    return "127.0.0.1"


@router.get("/local-ip")
def get_local_ip():
    """返回本机局域网 IP，前端用于确定扫描网段"""
    return {"ip": _get_lan_ip()}


# ============================================================
# 设备扫描（后端执行，绕过浏览器 PNA 限制）
# ============================================================

async def _try_port(ip: str, port: int, timeout: float) -> bool:
    """用 asyncio websockets 试探单个端口"""
    try:
        async with asyncio.timeout(timeout):
            ws = await websockets.connect(
                f"ws://{ip}:{port}",
                max_size=10 * 1024 * 1024,
                open_timeout=timeout,
                close_timeout=0.5,
            )
            await ws.close()
            return True
    except Exception:
        return False


async def _scan_subnet(subnet: str, start: int, end: int,
                       telemetry_port: int, frame_port: int,
                       timeout: float) -> list[dict]:
    """扫描 subnet 网段中指定范围的 IP"""
    results: list[dict] = []
    sem = asyncio.Semaphore(30)  # 限制并发数

    async def probe(ip: str):
        async with sem:
            t_task = _try_port(ip, telemetry_port, timeout)
            f_task = _try_port(ip, frame_port, timeout)
            t, f = await asyncio.gather(t_task, f_task)
            if t or f:
                results.append({"ip": ip, "telemetry": t, "frame": f})

    tasks = [probe(f"{subnet}.{i}") for i in range(start, end + 1)]
    await asyncio.gather(*tasks)
    return results


@router.post("/scan")
async def scan_devices(
    telemetry_port: int = 8001,
    frame_port: int = 8002,
    timeout: float = 1.0,
):
    """扫描局域网设备（WS 端口探测），返回发现的设备列表"""
    ip = _get_lan_ip()
    subnet = ip[:ip.rfind(".")]

    devices = await _scan_subnet(subnet, 1, 254, telemetry_port, frame_port, timeout)
    return {"subnet": subnet, "devices": devices, "total": len(devices)}
