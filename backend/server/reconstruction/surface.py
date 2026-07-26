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


def reconstruct_surface(points: np.ndarray, config: dict,
                        colors: np.ndarray | None = None,
                        color_ref: np.ndarray | None = None) -> str | None:
    """将点云转为三角网格并导出 PLY 文件

    Args:
        points: (N, 3) 点云, 世界坐标系, 米 (fused 几何)
        config: 项目配置
        colors: (M, 3) uint8 RGB 颜色, 与 color_ref 对齐
        color_ref: (M, 3) pre-fuse 点云 (点数 = len(colors)), 用于颜色传递

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

    # 1. 创建 Open3D 点云 (仅几何，Poisson 重建用)
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

    # 6.5 颜色传递: 用 color_ref (pre-fuse) 的 KD 树 → mesh 顶点着色
    has_color = (colors is not None and color_ref is not None
                 and len(colors) == len(color_ref) and len(colors) > 0)
    if has_color:
        try:
            # 用带颜色的 pre-fuse 点云做 KD 树参考
            ref_pcd = o3d.geometry.PointCloud()
            ref_pcd.points = o3d.utility.Vector3dVector(color_ref.astype(np.float64))
            ref_pcd.colors = o3d.utility.Vector3dVector(colors.astype(np.float64) / 255.0)
            ref_pcd = ref_pcd.voxel_down_sample(voxel_size=voxel_size * 2)  # 粗采样加速
            pts_src = np.asarray(ref_pcd.points)
            colors_src = np.asarray(ref_pcd.colors)
            mesh_verts = np.asarray(mesh.vertices)
            from scipy.spatial import KDTree
            tree = KDTree(pts_src)
            k = min(5, len(pts_src))
            _, idx = tree.query(mesh_verts, k=k)
            if k == 1:
                mesh_colors = colors_src[idx]
            else:
                weights = 1.0 / (np.linalg.norm(mesh_verts[:, None, :] - pts_src[idx], axis=2) + 1e-8)
                weights /= weights.sum(axis=1, keepdims=True)
                mesh_colors = np.sum(colors_src[idx] * weights[:, :, None], axis=1)
            mesh.vertex_colors = o3d.utility.Vector3dVector(mesh_colors)
        except ImportError:
            pass  # scipy 不可用, 跳过颜色传递

    # 7. 导出 PLY (顶点 + 面)
    output_dir = config.get('output', {}).get('point_cloud_dir', 'output')
    os.makedirs(output_dir, exist_ok=True)
    filename = f"mesh_{time.time():.0f}.ply"
    filepath = os.path.join(output_dir, filename)

    o3d.io.write_triangle_mesh(filepath, mesh)
    url = f"/{output_dir}/{filename}"

    verts = np.asarray(mesh.vertices, dtype=np.float32)
    faces = np.asarray(mesh.triangles, dtype=np.int32)

    vc: list = []
    if mesh.has_vertex_colors():
        vc_arr = (np.clip(np.asarray(mesh.vertex_colors), 0, 1) * 255).astype(np.uint8)
        vc = vc_arr.ravel().tolist()

    elapsed = (time.perf_counter() - t0) * 1000
    logger.info("表面重建完成: %d verts, %d faces, %s, %.0fms → %s",
                len(verts), len(faces),
                "有颜色" if vc else "无颜色",
                elapsed, url)
    return {
        "url": url,
        "mesh": {
            "vertices": verts.ravel().tolist(),
            "faces": faces.ravel().tolist(),
            "vertex_count": int(len(verts)),
            "face_count": int(len(faces)),
            "vertex_colors": vc,
        },
    }
