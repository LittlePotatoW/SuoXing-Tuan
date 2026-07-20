# ============================================================
# backend/server/reconstruction/tsdf.py
# TSDF 体素融合：逐帧 RGBDImage → integrate → marching cubes
#
# 设计与用法:
#   导出 reconstruct_tsdf(frames, positions, config) → dict | None
#   每帧 depth_m(H,W) + 位姿 + 相机内参 → RGBDImage → integrate
#   与 Poisson 互斥，由 engine._trigger 根据 method 路由
# ============================================================

import base64
import logging
import os
import time

import numpy as np

logger = logging.getLogger(__name__)


def reconstruct_tsdf(frames, positions, config: dict) -> dict | None:
    """逐帧 TSDF 积分 → marching cubes → 输出 mesh 数据

    Args:
        frames: FrameEntry 列表，每个含 depth_m (H,W) float32 深度米
        positions: [{x, y, heading}, ...] 每帧世界位姿
        config: 项目配置
    """
    import open3d as o3d

    tsdf_cfg = config.get('reconstruction', {}).get('tsdf', {})
    depth_cfg = config.get('depth_camera', {})
    depth_proc = config.get('depth', {})

    vl = tsdf_cfg.get('voxel_length', 0.05)
    st = tsdf_cfg.get('sdf_trunc', 0.10)
    max_depth = depth_proc.get('max_depth', 6.0)

    # 相机内参（subsample 后的宽高从 depth_m shape 取）
    w_orig = depth_cfg.get('width', 640)
    h_orig = depth_cfg.get('height', 480)
    fx = depth_cfg.get('fx', 573.0)
    fy = depth_cfg.get('fy', 572.0)
    cx = depth_cfg.get('cx', 320.0)
    cy = depth_cfg.get('cy', 240.0)
    subsample = depth_proc.get('subsample', 4)

    # 第一帧有效 depth_m 确定 subsample 后的尺寸
    dm_sample = None
    for f in frames:
        if f.depth_m is not None:
            dm_sample = f.depth_m
            break
    if dm_sample is None:
        logger.warning("TSDF: 无有效深度图")
        return None

    h, w = dm_sample.shape
    scale = w_orig / w  # subsample 等比缩放
    intrinsic = o3d.camera.PinholeCameraIntrinsic(
        int(w), int(h), fx / scale, fy / scale, cx / scale, cy / scale,
    )

    volume = o3d.pipelines.integration.ScalableTSDFVolume(
        voxel_length=vl, sdf_trunc=st,
        color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGBD,
    )

    integrated = 0
    for f, pose in zip(frames, positions):
        dm = f.depth_m
        if dm is None:
            continue

        depth_mm = (dm * 1000).clip(0, 65535).astype(np.uint16)
        depth_o3d = o3d.geometry.Image(depth_mm)

        # 解码 RGB 图作为颜色
        color_o3d = None
        try:
            import cv2
            img_bytes = base64.b64decode(f.image)
            img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
            bgr = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
            if bgr is not None:
                if bgr.shape[:2] != (h, w):
                    bgr = cv2.resize(bgr, (w, h))
                color_o3d = o3d.geometry.Image(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.uint8))
        except Exception:
            pass
        if color_o3d is None:
            color_o3d = o3d.geometry.Image(np.zeros((h, w, 3), dtype=np.uint8))

        rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(
            color_o3d, depth_o3d,
            depth_scale=1000.0, depth_trunc=max_depth,
            convert_rgb_to_intensity=False,
        )

        # 相机→世界位姿（与 mapper._camera_to_world 一致的三步变换）
        ext_cfg = config.get('camera_to_vehicle', {})
        ext_rot = ext_cfg.get('rotation', [0.0, 0.0, 0.0])
        ext_trans = ext_cfg.get('translation', [0.0, 0.0, 0.0])
        # Step 1: 相机坐标系 → 车体坐标系（轴对齐）
        # 相机 Z前→车体 X前, X右→-Y左, Y下→-Z上
        rot_cam2veh = np.eye(4)
        rot_cam2veh[:3, :3] = np.array([
            [-1, 0,  0],   # 相机 Z → vehicle X
            [0,  0, -1],   # 相机 X → vehicle -Y
            [0,  1,  0],   # 相机 Y → vehicle -Z
        ])
        # 绕相机 X 轴旋转 90°（立起躺倒的点云）
        rot_cam2veh[:3, :3] = rot_cam2veh[:3, :3] @ np.array([
            [1, 0,  0],
            [0, 0,  1],
            [0, -1, 0],
        ])
        # 相机 Z 轴旋转（角度从 config 读，默认 0，正=逆时针）
        cam_z_angle = tsdf_cfg.get('cam_rotate_deg', 0)
        if cam_z_angle != 0:
            a = np.radians(cam_z_angle)
            Rz = np.array([[np.cos(a), -np.sin(a), 0],
                           [np.sin(a),  np.cos(a), 0],
                           [0,          0,         1]])
            rot_cam2veh[:3, :3] = rot_cam2veh[:3, :3] @ Rz
        # Step 2: 相机安装外参（ZYX Euler → 4x4 旋转）
        r, p, y = np.radians(ext_rot)
        cr, sr = np.cos(r), np.sin(r)
        cp, sp = np.cos(p), np.sin(p)
        cy, sy = np.cos(y), np.sin(y)
        rot_ext = np.eye(4)
        rot_ext[:3, :3] = np.array([
            [cy*cp, cy*sp*sr - sy*cr, cy*sp*cr + sy*sr],
            [sy*cp, sy*sp*sr + cy*cr, sy*sp*cr - cy*sr],
            [-sp,   cp*sr,            cp*cr],
        ])
        rot_ext[0, 3] = ext_trans[0]
        rot_ext[1, 3] = ext_trans[1]
        rot_ext[2, 3] = ext_trans[2]
        # Step 3: 车体 → 世界（heading 旋转 + 位置平移）
        heading_rad = np.radians(pose['heading'])
        cos_h, sin_h = np.cos(heading_rad), np.sin(heading_rad)
        veh2world = np.eye(4)
        veh2world[:3, :3] = np.array([
            [cos_h, -sin_h, 0],
            [sin_h,  cos_h, 0],
            [0,      0,     1],
        ])
        veh2world[0, 3] = pose['x']
        veh2world[1, 3] = pose['y']
        # T = veh2world @ rot_ext @ rot_cam2veh
        T = veh2world @ rot_ext @ rot_cam2veh

        volume.integrate(rgbd, intrinsic, T)
        integrated += 1

    if integrated == 0:
        logger.warning("TSDF: 无帧被积分")
        return None

    mesh = volume.extract_triangle_mesh()
    if len(mesh.vertices) == 0:
        logger.warning("TSDF: mesh 为空")
        return None

    verts = np.asarray(mesh.vertices, dtype=np.float32)
    faces = np.asarray(mesh.triangles, dtype=np.int32)

    vc: list = []
    if mesh.has_vertex_colors():
        vc = (np.clip(np.asarray(mesh.vertex_colors), 0, 1) * 255).astype(np.uint8).ravel().tolist()

    output_dir = config.get('output', {}).get('point_cloud_dir', 'output')
    os.makedirs(output_dir, exist_ok=True)
    fname = f"tsdf_{time.time():.0f}.ply"
    fpath = os.path.join(output_dir, fname)
    o3d.io.write_triangle_mesh(fpath, mesh)
    url = f"/{output_dir}/{fname}"

    logger.info("TSDF 重建完成: %d 帧积分, %d verts, %d faces, %s → %s",
                integrated, len(verts), len(faces),
                "有颜色" if vc else "无颜色",
                url)
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
