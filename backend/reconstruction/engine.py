# ============================================================
#  文件: backend/reconstruction/engine.py
#  所属: SuoXing-Tuan / V2 三维重建管线
#  职责: 累积世界坐标系点云 → 表面重建(Mesh) → 输出结果
#  依赖: Open3D, NumPy
# ============================================================

# ============================================================
#  ⚙️ 可调参数 — 修改重建行为从这里改
# ============================================================

# 降采样体素大小（米）。越小越精细但越慢。
# 0.01=1cm(标准), 0.005=5mm(精细), 0.02=2cm(快速预览)
VOXEL_SIZE = 0.01

# 每隔多少帧触发一次表面重建。越小前端更新越频繁。
REBUILD_INTERVAL_FRAMES = 10

# 全局点云最大点数。超过后自动降采样减半，防止内存溢出。
MAX_POINTS = 2_000_000

# Poisson 重建深度 (6~10)。越高越精细但计算量指数增长。
POISSON_DEPTH = 8

# 离群点剔除: 统计滤波邻居数 / 标准差倍数
OUTLIER_NB_NEIGHBORS = 20
OUTLIER_STD_RATIO = 2.0

# 去掉密度最低的 N% 三角面（Poisson 会产生伪面）
DENSITY_FILTER_PERCENTILE = 0.10

# ============================================================
#  代码
# ============================================================

import logging
import time

import numpy as np

from common.schemas import (
    FusedFrame, ReconstructionResult, MeshData, CrackAnnotation, Vector3,
)

logger = logging.getLogger("reconstruction.engine")


class ReconstructionEngine:
    """
    三维重建引擎 — 纯 CPU，不占 GPU。
    三张 4090 留给 YOLO 推理。
    """

    def __init__(
        self,
        voxel_size: float = VOXEL_SIZE,
        rebuild_interval_frames: int = REBUILD_INTERVAL_FRAMES,
        max_points: int = MAX_POINTS,
    ):
        self.voxel_size = voxel_size
        self.rebuild_interval_frames = rebuild_interval_frames
        self.max_points = max_points

        # 内部状态
        self._point_blocks: list[np.ndarray] = []    # 累积的点云块
        self._camera_trail: list[list[float]] = []   # 相机轨迹 [[x,y,z], ...]
        self._frame_count: int = 0
        self._total_points: int = 0
        self._last_rebuild_at_frame: int = 0
        self._latest_mesh: MeshData | None = None
        self._cracks: list[CrackAnnotation] = []
        self._status: str = "accumulating"

    # ================================================================
    #  对外接口
    # ================================================================

    def add_frame(self, frame: FusedFrame) -> None:
        """接收一帧融合数据。到达阈值时自动触发表面重建。"""
        if frame.point_count == 0:
            return

        pts = np.array(frame.points_world, dtype=np.float64).reshape(-1, 3)
        self._point_blocks.append(pts)
        self._total_points += pts.shape[0]
        self._frame_count += 1

        for cam in frame.cameras_world:
            self._camera_trail.append([cam.position.x, cam.position.y, cam.position.z])

        if self._total_points > self.max_points:
            self._compact_points()

        if self._frame_count - self._last_rebuild_at_frame >= self.rebuild_interval_frames:
            self._rebuild()

    def add_crack(self, x: float, y: float, z: float,
                  confidence: float = 1.0, crack_type: str = "",
                  frame_id: str = "") -> None:
        """添加裂缝的 3D 标注。"""
        self._cracks.append(CrackAnnotation(
            position=Vector3(x=x, y=y, z=z),
            confidence=confidence,
            crack_type=crack_type,
            image_frame_id=frame_id,
        ))

    def get_result(self) -> ReconstructionResult:
        """返回当前最新重建结果。"""
        return ReconstructionResult(
            status=self._status,
            mesh=self._latest_mesh or MeshData(),
            cracks=self._cracks,
            camera_trail=self._camera_trail,
            total_frames=self._frame_count,
            total_points=self._total_points,
        )

    @property
    def frame_count(self) -> int:
        return self._frame_count

    # ================================================================
    #  内部: 表面重建
    # ================================================================

    def _rebuild(self) -> None:
        """合并 → 降采样 → 去飞点 → 法线 → Poisson → 去伪面"""
        self._status = "running"
        t0 = time.perf_counter()

        try:
            if not self._point_blocks:
                self._status = "accumulating"
                return

            merged = np.vstack(self._point_blocks)
            logger.info("Rebuild #%d: %d points", self._frame_count, merged.shape[0])

            mesh = self._reconstruct_surface(merged)

            if mesh is not None:
                verts = np.asarray(mesh.vertices)
                faces = np.asarray(mesh.triangles)
                self._latest_mesh = MeshData(
                    vertices=verts.ravel().tolist(),
                    faces=faces.ravel().tolist(),
                    vertex_count=verts.shape[0],
                    face_count=faces.shape[0],
                )

            self._status = "completed"
            self._last_rebuild_at_frame = self._frame_count

        except Exception as e:
            logger.error("Rebuild failed: %s", e, exc_info=True)
            self._status = "error"

        elapsed = (time.perf_counter() - t0) * 1000
        v = self._latest_mesh.vertex_count if self._latest_mesh else 0
        f = self._latest_mesh.face_count if self._latest_mesh else 0
        logger.info("Rebuild done: %d verts, %d faces, %.0fms", v, f, elapsed)

    def _reconstruct_surface(self, points: np.ndarray):
        """核心: 点云 → 三角网格。"""
        import open3d as o3d

        # 1. 创建点云
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)

        # 2. 体素降采样
        pcd = pcd.voxel_down_sample(voxel_size=self.voxel_size)
        if len(pcd.points) < 10:
            logger.warning("Too few points after downsampling")
            return None

        # 3. 去离群点
        pcd, _ = pcd.remove_statistical_outlier(
            nb_neighbors=OUTLIER_NB_NEIGHBORS, std_ratio=OUTLIER_STD_RATIO
        )

        # 4. 估算法线
        pcd.estimate_normals(
            o3d.geometry.KDTreeSearchParamHybrid(
                radius=self.voxel_size * 5, max_nn=30
            )
        )

        # 5. 统一法线方向
        pcd.orient_normals_towards_camera_location(np.array([0.0, 0.0, 0.0]))

        # 6. Poisson 表面重建
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd, depth=POISSON_DEPTH, width=0, scale=1.1, linear_fit=False
        )

        # 7. 去低密度伪面
        threshold = np.quantile(densities, DENSITY_FILTER_PERCENTILE)
        mesh.remove_vertices_by_mask(densities < threshold)

        return mesh

    # ================================================================
    #  内部: 内存管理
    # ================================================================

    def _compact_points(self) -> None:
        """点太多时降采样，防 OOM。"""
        if not self._point_blocks:
            return
        merged = np.vstack(self._point_blocks)
        keep = max(1, merged.shape[0] // (self.max_points // 2))
        self._point_blocks = [merged[::keep]]
        self._total_points = self._point_blocks[0].shape[0]
        logger.info("Compacted: %d points", self._total_points)
