# ============================================================
# backend/loader/scene_loader.py
# 离线场景数据加载器 — 读文件夹(PLY+poses.json)→SensorFrame→重建管线
#
# 数据文件夹结构:
#   backend/data/<scene-name>/
#   ├── pointclouds/         # .ply 文件, 按帧序号
#   ├── poses.json           # [{frame, x, y, z, qw, qx, qy, qz}, ...]
#   └── config.json          # (可选) 传感器外参
# ============================================================

import json
import asyncio
import logging
from pathlib import Path
from typing import Optional

import numpy as np

from reconstruction.schemas import (
    SensorFrame, PointCloudData, CarPosition, Pose6DoF, Vector3, Quaternion,
)

logger = logging.getLogger("loader")


class SceneLoader:
    """读取文件夹中的 PLY 点云 + 位姿，逐帧构造 SensorFrame 推入重建管线"""

    def __init__(self, scene_path: str):
        self.scene_path = Path(scene_path)
        if not self.scene_path.exists():
            raise FileNotFoundError(f"Scene path not found: {scene_path}")

        self._frames: list[dict] = []    # [{ply_path, pose}]
        self._index = 0
        self._running = False
        self._task: Optional[asyncio.Task] = None

        self._scan()

    # ── 扫描文件夹 ──

    def _scan(self):
        pc_dir = self.scene_path / "pointclouds"
        if not pc_dir.exists():
            raise FileNotFoundError(f"pointclouds/ not found in {self.scene_path}")

        ply_files = sorted(pc_dir.glob("*.ply"))
        if not ply_files:
            raise FileNotFoundError(f"No .ply files found in {pc_dir}")

        # 读取位姿
        poses = self._load_poses()
        # 可选的外参配置
        self._config = self._load_config()

        self._frames = []
        for i, ply_path in enumerate(ply_files):
            pose = poses[i] if i < len(poses) else {"x": 0, "y": 0, "z": 0, "qw": 1, "qx": 0, "qy": 0, "qz": 0}
            self._frames.append({"ply_path": ply_path, "pose": pose})

        logger.info("SceneLoader: %d frames found in %s", len(self._frames), self.scene_path.name)

    def _load_poses(self) -> list[dict]:
        pose_file = self.scene_path / "poses.json"
        if not pose_file.exists():
            logger.warning("poses.json not found, using identity poses")
            return []
        with open(pose_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_config(self) -> dict:
        cfg_file = self.scene_path / "config.json"
        if not cfg_file.exists():
            return {}
        with open(cfg_file, "r", encoding="utf-8") as f:
            return json.load(f)

    # ── 帧加载 ──

    @property
    def total_frames(self) -> int:
        return len(self._frames)

    @property
    def current_index(self) -> int:
        return self._index

    @property
    def is_running(self) -> bool:
        return self._running

    def load_frame(self, index: int) -> Optional[SensorFrame]:
        """读取第 index 帧，构造 SensorFrame"""
        if index < 0 or index >= len(self._frames):
            return None

        item = self._frames[index]
        ply_path = item["ply_path"]
        pose = item["pose"]

        # 读取点云（优先 Open3D，不可用时用纯 Python 解析 ASCII PLY）
        pts = self._read_ply(str(ply_path))

        return SensorFrame(
            frame_id=f"frame_{index:06d}",
            point_cloud=PointCloudData(
                points=pts,
                point_count=len(pts) // 3,
            ),
            car_position=CarPosition(
                pose=Pose6DoF(
                    position=Vector3(x=pose.get("x", 0), y=pose.get("y", 0), z=pose.get("z", 0)),
                    rotation=Quaternion(
                        qw=pose.get("qw", 1), qx=pose.get("qx", 0),
                        qy=pose.get("qy", 0), qz=pose.get("qz", 0),
                    ),
                ),
            ),
            camera_views=[],
        )

    # ── PLY 读取 ──

    @staticmethod
    def _read_ply(path: str) -> list[float]:
        """读取 ASCII PLY 文件，返回扁平点列表 [x0,y0,z0, x1,y1,z1, ...]"""
        try:
            import open3d as o3d
            pcd = o3d.io.read_point_cloud(path)
            pts = np.asarray(pcd.points, dtype=np.float32)
            if pts.size > 0:
                return pts.flatten().tolist()
        except Exception:
            pass

        # fallback: 纯 Python 解析 ASCII PLY
        pts = []
        with open(path, "r") as f:
            in_header = True
            count = 0
            for line in f:
                if in_header:
                    if line.startswith("element vertex"):
                        count = int(line.split()[-1])
                    if line.strip() == "end_header":
                        in_header = False
                    continue
                parts = line.strip().split()
                if len(parts) >= 3:
                    try:
                        pts.extend([float(parts[0]), float(parts[1]), float(parts[2])])
                    except ValueError:
                        continue
        return pts

    # ── 回放控制 ──

    async def run(self, interval: float = 0.05, on_frame=None, on_complete=None):
        """逐帧回放：加载 → 回调 on_frame → 等待 interval"""
        self._running = True
        self._index = 0

        try:
            for i in range(len(self._frames)):
                if not self._running:
                    break
                self._index = i
                frame = self.load_frame(i)
                if frame and on_frame:
                    await on_frame(frame, i)
                await asyncio.sleep(interval)
        finally:
            self._running = False
            if on_complete:
                await on_complete()

    def pause(self):
        self._running = False

    def resume(self):
        self._running = True

    def stop(self):
        self._running = False
        self._index = 0

    def seek(self, index: int):
        if 0 <= index < len(self._frames):
            self._index = index
