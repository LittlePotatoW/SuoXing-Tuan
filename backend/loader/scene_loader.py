# ============================================================
# backend/loader/scene_loader.py
# 离线场景数据加载器 — 读文件夹(PLY+poses.json)→SensorFrame→重建管线
#
# 数据文件夹结构:
#   backend/data/<scene-name>/
#   ├── pointclouds/         # .ply 文件, 按帧序号
#   ├── images/              # (可选) .jpg 文件, 与点云帧一一对应
#   ├── poses.json           # [{frame, x, y, z, qw, qx, qy, qz}, ...]
#   └── config.json          # (可选) 传感器外参 + 相机内参
# ============================================================

import json
import asyncio
import logging
from pathlib import Path
from typing import Optional

import numpy as np

from common.schemas import (
    SensorFrame, PointCloudData, CarPosition, CameraView,
    Pose6DoF, Vector3, Quaternion,
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
        self._paused = False
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

        # 读取位姿 + 配置
        poses = self._load_poses()
        self._config = self._load_config()

        # 检测 images/ 目录
        self._images_dir = self.scene_path / "images"
        self._has_images = self._images_dir.exists()

        self._frames = []
        for i, ply_path in enumerate(ply_files):
            pose = poses[i] if i < len(poses) else {"x": 0, "y": 0, "z": 0, "qw": 1, "qx": 0, "qy": 0, "qz": 0}
            self._frames.append({"ply_path": ply_path, "pose": pose, "index": i})

        logger.info("SceneLoader: %d frames, images=%s, in %s",
                     len(self._frames), self._has_images, self.scene_path.name)

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
        """读取第 index 帧，构造 SensorFrame（含相机图像，如有）"""
        if index < 0 or index >= len(self._frames):
            return None

        item = self._frames[index]
        ply_path = item["ply_path"]
        pose = item["pose"]
        frame_idx = item["index"]

        # 读取点云（优先 Open3D，不可用时用纯 Python 解析 ASCII PLY）
        pts = self._read_ply(str(ply_path))

        # 构造相机视图（加载图片）
        camera_views: list[CameraView] = []
        if self._has_images:
            img_path = self._images_dir / f"{frame_idx:06d}.jpg"
            if img_path.exists():
                try:
                    with open(img_path, "rb") as f:
                        img_data = f.read()
                    # 从 config 读取相机参数
                    cam_cfg = self._config.get("camera", {})
                    cam_pose_cfg = cam_cfg.get("position", [0.0, 0.0, 1.0])
                    cam_rot_cfg = cam_cfg.get("rotation", [1.0, 0.0, 0.0, 0.0])
                    camera_views.append(CameraView(
                        image_data=img_data,
                        width=cam_cfg.get("width", 544),
                        height=cam_cfg.get("height", 384),
                        camera_pose=Pose6DoF(
                            position=Vector3(
                                x=cam_pose_cfg[0], y=cam_pose_cfg[1], z=cam_pose_cfg[2],
                            ),
                            rotation=Quaternion(
                                qw=cam_rot_cfg[0], qx=cam_rot_cfg[1],
                                qy=cam_rot_cfg[2], qz=cam_rot_cfg[3],
                            ),
                        ),
                    ))
                except Exception as exc:
                    logger.warning("Failed to load image %s: %s", img_path, exc)

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
            camera_views=camera_views,
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

    async def run(self, interval: float = 0.05, on_frame=None, on_complete=None,
                  from_beginning: bool = True):
        """逐帧回放：加载 → 回调 on_frame → 等待 interval"""
        self._running = True
        self._paused = False
        if from_beginning:
            self._index = 0

        try:
            for i in range(self._index, len(self._frames)):
                if not self._running:
                    break
                self._index = i
                frame = self.load_frame(i)
                if frame and on_frame:
                    await on_frame(frame, i)
                await asyncio.sleep(interval)
        finally:
            self._running = False
            if on_complete and not self._paused:
                await on_complete()

    def pause(self):
        self._running = False
        self._paused = True

    def resume(self):
        self._running = True
        self._paused = False

    def stop(self):
        self._running = False
        self._index = 0

    def seek(self, index: int):
        if 0 <= index < len(self._frames):
            self._index = index
