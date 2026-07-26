#!/usr/bin/env python3
"""
ws_stream_server.py (Python 3)
===============================
Reads encoded frames from frame_bridge (tcp://127.0.0.1:8004)
and broadcasts them via WebSocket to clients on port 8002.

Protocol (compatible with wzm viewer):
  {"type":"frame","timestamp":...,"image":"<base64 JPEG>","depth_map":"<base64 PNG>"}
  {"type":"ping"}  /  {"type":"pong"}
  {"type":"status","message":"camera_ready"}

Usage:
    python3 ws_stream_server.py [--port 8002] [--bridge-port 8004]
"""
import asyncio
import json
import socket
import time
import argparse
import logging

import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("ws-stream")


class FrameSource:
    """Connects to frame_bridge TCP and yields frames as JSON strings."""

    def __init__(self, host="127.0.0.1", port=8004):
        self.host = host
        self.port = port
        self._buf = b""

    async def connect(self):
        """Establish TCP connection to frame_bridge (in thread, since it's blocking)."""
        loop = asyncio.get_event_loop()

        def _connect():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            sock.settimeout(2.0)
            return sock

        self._sock = await loop.run_in_executor(None, _connect)
        log.info("Connected to frame bridge tcp://%s:%d", self.host, self.port)

    async def read_frame(self):
        """Read one complete JSON line from TCP. Returns dict or None."""
        loop = asyncio.get_event_loop()

        while b"\n" not in self._buf:
            try:
                chunk = await loop.run_in_executor(None, self._sock.recv, 65536)
            except socket.timeout:
                continue
            except Exception as e:
                log.error("TCP recv error: %s", e)
                return None
            if not chunk:
                log.warning("TCP connection closed by bridge")
                return None
            self._buf += chunk

        line, self._buf = self._buf.split(b"\n", 1)
        try:
            return json.loads(line.decode("ascii"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            log.warning("Frame parse error: %s", e)
            return None

    def close(self):
        try:
            self._sock.close()
        except Exception:
            pass


class WsStreamServer:
    """WebSocket server broadcasting frames in wzm-compatible format."""

    def __init__(self, ws_port=8002, bridge_port=8004):
        self.ws_port = ws_port
        self.bridge_port = bridge_port
        self._clients = set()
        self._latest_frame = None  # {"ts":..., "image":..., "depth_map":...}

    async def _frame_reader(self, source):
        """Continuously read frames from bridge into self._latest_frame."""
        while True:
            frame = await source.read_frame()
            if frame is not None:
                self._latest_frame = {
                    "timestamp": frame["timestamp"],
                    "image": frame["image"],
                    "depth_map": frame["depth_map"],
                }
            await asyncio.sleep(0.001)

    async def _handler(self, websocket, path):
        peer = websocket.remote_address
        log.info("WS client connected: %s:%s", *peer)
        self._clients.add(websocket)

        # Send ready message (wzm protocol)
        try:
            await websocket.send(json.dumps({
                "type": "status",
                "message": "camera_ready",
            }))
        except Exception:
            pass

        # Start send + receive tasks
        send_task = asyncio.ensure_future(self._sender(websocket))
        recv_task = asyncio.ensure_future(self._receiver(websocket))

        done, pending = await asyncio.wait(
            [send_task, recv_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

        self._clients.discard(websocket)
        log.info("WS client disconnected: %s:%s", *peer)

    async def _sender(self, websocket):
        """Send frames + heartbeat to one client."""
        last_heartbeat = time.time()
        last_frame_ts = 0

        while True:
            now = time.time()

            # Heartbeat every 30s
            if now - last_heartbeat >= 30:
                try:
                    await asyncio.wait_for(
                        websocket.send(json.dumps({"type": "ping"})),
                        timeout=2.0,
                    )
                    last_heartbeat = now
                except Exception:
                    return

            # Send latest frame if new
            if self._latest_frame and self._latest_frame["timestamp"] != last_frame_ts:
                ts = self._latest_frame["timestamp"]
                msg = json.dumps({
                    "type": "frame",
                    "timestamp": ts,
                    "image": self._latest_frame["image"],
                    "depth_map": self._latest_frame["depth_map"],
                })
                try:
                    await asyncio.wait_for(websocket.send(msg), timeout=2.0)
                    last_frame_ts = ts
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    return

            await asyncio.sleep(0.01)

    async def _receiver(self, websocket):
        """Handle client commands (ping/pong, control)."""
        while True:
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                msg = json.loads(raw)
                t = msg.get("type", "")
                if t == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))
                elif t == "control":
                    log.info("Control command: %s", msg.get("command", "?"))
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            except Exception:
                return

    async def serve(self):
        """Start frame reader + WebSocket server."""
        source = FrameSource(port=self.bridge_port)
        await source.connect()

        # Start frame reader background task
        asyncio.ensure_future(self._frame_reader(source))

        log.info("WebSocket server: ws://0.0.0.0:%d", self.ws_port)
        log.info("Bridge: tcp://127.0.0.1:%d", self.bridge_port)

        async with websockets.serve(
            self._handler, "0.0.0.0", self.ws_port,
            max_size=10 * 1024 * 1024,  # 10MB max message
        ):
            await asyncio.Future()  # run forever


# ==========================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Astra Pro WebSocket Stream Server")
    parser.add_argument("--port", type=int, default=8002, help="WebSocket port")
    parser.add_argument("--bridge-port", type=int, default=8004, help="Frame bridge TCP port")
    args = parser.parse_args()

    print("=" * 55)
    print("  Astra Pro WS Stream Server (wzm-compatible)")
    print("  Frame source: tcp://127.0.0.1:%d" % args.bridge_port)
    print("  WebSocket:    ws://0.0.0.0:%d" % args.port)
    print("  Format:       16-bit depth PNG + JPEG RGB")
    print("  Ctrl+C to stop")
    print("=" * 55)

    srv = WsStreamServer(ws_port=args.port, bridge_port=args.bridge_port)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(srv.serve())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
