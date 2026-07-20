# ============================================================
# backend/server/reconstruction/fusion.py
# 多帧融合：全量重建 / 增量重建，体素降采样
#
# 设计与用法:
#   导出 fuse() 函数
#   输入: 新点云 + 旧结果(可选) + mode + voxel_size
#   输出: 融合后的点云
# ============================================================
#   mode="full"        每次重建独立, 旧结果丢弃
#   mode="incremental" 新旧点云合并后降采样
#   skip_downsample    True 时只合并不降采样(surface重建用)
# ============================================================

import logging

import numpy as np

logger = logging.getLogger(__name__)


def fuse(new_cloud: np.ndarray,
         previous: np.ndarray | None = None,
         mode: str = "incremental",
         voxel_size: float = 0.01,
         skip_downsample: bool = False) -> np.ndarray | None:
    """融合点云

    Args:
        new_cloud:      新重建的点云 (N, 3)
        previous:       上一次融合结果 (M, 3), full 模式忽略
        mode:           "full" 全量 / "incremental" 增量
        voxel_size:     体素降采样大小 (m)
        skip_downsample: True 时只合并，不降采样（surface 重建已做降采样）

    Returns:
        融合后的点云 (K, 3), 单位米
    """
    if new_cloud is None or len(new_cloud) == 0:
        return previous

    if mode == "full" or previous is None:
        merged = new_cloud
    else:
        merged = np.vstack([previous, new_cloud])

    if skip_downsample or voxel_size <= 0:
        logger.debug("fuse: mode=%s, %d 点 (跳过降采样)", mode, len(merged))
        return merged.astype(np.float32)

    before = len(merged)
    try:
        merged = _voxel_downsample_o3d(merged, voxel_size)
        logger.info("降采样: Open3D voxel_down_sample, %d → %d 点, voxel=%.3f",
                    before, len(merged), voxel_size)
    except Exception:
        merged = _voxel_downsample(merged, voxel_size)
        logger.warning("降采样: 回退到 Python dict 循环, %d → %d 点, voxel=%.3f",
                       before, len(merged), voxel_size)

    return merged.astype(np.float32)


def _voxel_downsample_o3d(pc: np.ndarray, size: float) -> np.ndarray:
    """Open3D C++ 体素降采样"""
    import open3d as o3d
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pc.astype(np.float64))
    pcd = pcd.voxel_down_sample(voxel_size=size)
    return np.asarray(pcd.points, dtype=np.float32)


def _voxel_downsample(pc: np.ndarray, size: float) -> np.ndarray:
    """体素降采样: 每个体素格内保留一个点 (质心) — Python fallback"""
    if size <= 0 or len(pc) == 0:
        return pc

    voxel_indices = np.floor(pc / size).astype(np.int64)
    voxel_map: dict[tuple, list] = {}
    for i, vi in enumerate(voxel_indices):
        key = (int(vi[0]), int(vi[1]), int(vi[2]))
        if key not in voxel_map:
            voxel_map[key] = [pc[i], 1]
        else:
            voxel_map[key][0] += pc[i]
            voxel_map[key][1] += 1

    centroids = np.array([
        acc[0] / acc[1] for acc in voxel_map.values()
    ], dtype=np.float32)
    return centroids
