# ============================================================
# backend/server/reconstruction/surface.py
# Poisson 表面重建：点云 → 三角网格 (Mesh)
#
# 设计与用法:
#   导出 reconstruct_surface(points, config) → mesh_ply_path | None
#   浅耦合: 输入 fuse() 的输出点云, 输出 PLY 文件路径
#   open3d 是可选依赖, 未安装时优雅降级
# ============================================================
#   poisson_depth     泊松深度 (6~10)
#   density_filter    去伪面比例 (0.10 = 去掉密度最低10%)
#   outlier_nb / outlier_std  离群点剔除参数
# ============================================================

import logging
import os
import time

import numpy as np

logger = logging.getLogger(__name__)


def reconstruct_surface(points: np.ndarray, config: dict) -> str | None:
    """将点云转为三角网格并导出 PLY 文件

    Args:
        points: (N, 3) 点云, 世界坐标系, 米
        config: 项目配置

    Returns:
        mesh PLY 文件 URL 路径, 或 None (失败/点数不够/无 open3d)
    """
    try:
        import open3d as o3d
    except ImportError:
        logger.warning("open3d 未安装, 无法进行表面重建")
        return None

    if points is None or len(points) < 10:
        logger.warning("点数不足 (%d), 无法进行表面重建", len(points) if points is not None else 0)
        return None

    recon_cfg = config.get('reconstruction', {})
    surface_cfg = recon_cfg.get('surface', {})
    voxel_size = recon_cfg.get('voxel_size', 0.05)

    depth = surface_cfg.get('poisson_depth', 8)
    outlier_nb = surface_cfg.get('outlier_nb', 20)
    outlier_std = surface_cfg.get('outlier_std', 2.0)
    density_pct = surface_cfg.get('density_filter', 0.10)

    t0 = time.perf_counter()
    logger.info("表面重建开始: %d 点, depth=%d, voxel=%.3f",
                len(points), depth, voxel_size)

    # 1. 创建 Open3D 点云
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points.astype(np.float64))

    # 2. 体素降采样
    pcd = pcd.voxel_down_sample(voxel_size=voxel_size)
    if len(pcd.points) < 10:
        logger.warning("降采样后点数不足 (%d)", len(pcd.points))
        return None

    # 3. 离群点剔除
    pcd, _ = pcd.remove_statistical_outlier(
        nb_neighbors=outlier_nb, std_ratio=outlier_std,
    )

    # 4. 法线估计
    pcd.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(
            radius=voxel_size * 5, max_nn=30,
        )
    )
    pcd.orient_normals_towards_camera_location(np.array([0.0, 0.0, 0.0]))

    # 5. Poisson 表面重建
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=depth, width=0, scale=1.1, linear_fit=False,
    )

    # 6. 去低密度伪面
    if density_pct > 0:
        threshold = np.quantile(densities, density_pct)
        mesh.remove_vertices_by_mask(densities < threshold)

    # 7. 导出 PLY (顶点 + 面)
    output_dir = config.get('output', {}).get('point_cloud_dir', 'output')
    os.makedirs(output_dir, exist_ok=True)
    filename = f"mesh_{time.time():.0f}.ply"
    filepath = os.path.join(output_dir, filename)

    o3d.io.write_triangle_mesh(filepath, mesh)
    url = f"/{output_dir}/{filename}"

    elapsed = (time.perf_counter() - t0) * 1000
    logger.info("表面重建完成: %d verts, %d faces, %.0fms → %s",
                len(mesh.vertices), len(mesh.triangles), elapsed, url)
    return url
