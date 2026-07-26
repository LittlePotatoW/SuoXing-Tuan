# Open3D TSDF 体素融合接入方案

## 一、当前方案 vs TSDF 对比

| | 当前 (fuse + Poisson) | TSDF |
|---|---|---|
| 帧处理方式 | 攒 30 帧批量合并 | 逐帧积分进体素 |
| 每帧开销 | 0（不处理） | ~5ms（integrate） |
| 触发时开销 | 体素降采样 + Poisson: 秒级 | marching cubes: 毫秒级 |
| mesh 质量 | 可能有伪面、翻转面 | 天然无伪面 |
| 动态物体过滤 | 无 | 体素自然加权，走过的人不留痕迹 |
| 内存 | 随点云量增长 | 固定（体素格大小决定） |

---

## 二、架构改动

### 2.1 新增文件

**`backend/server/reconstruction/tsdf.py`**

```python
# 核心: 维护一个 ScalableTSDFVolume, 提供 integrate() + extract_mesh()
# 每次重建结束后清空 volume 重建（或保留增量模式）

class TSDFManager:
    def __init__(self, voxel_size=0.05, sdf_trunc=0.1):
        self.voxel_size = voxel_size
        self.sdf_trunc = sdf_trunc
        self._volume = self._create_volume()

    def _create_volume(self):
        return o3d.pipelines.integration.ScalableTSDFVolume(
            voxel_length=self.voxel_size,
            sdf_trunc=self.sdf_trunc,
            color_type=o3d.pipelines.integration.TSDFVolumeColorType.NoColor
        )

    def integrate(self, pcd: o3d.geometry.PointCloud, pose: np.ndarray):
        self._volume.integrate(pcd, pose)  # 逐帧融合

    def extract_mesh(self):
        mesh = self._volume.extract_triangle_mesh()
        return mesh

    def reset(self):
        self._volume = self._create_volume()
```

### 2.2 修改文件

| 文件 | 改动 |
|------|------|
| `backend/config.yaml` | 新增 `reconstruction.tsdf` 段：`enabled`, `voxel_length`, `sdf_trunc` |
| `reconstruction/__init__.py` | +1 行导出 `TSDFManager` |
| `reconstruction/surface.py` | 新增 `reconstruct_tsdf(frames, positions, config)` 函数 |
| `engine/engine.py` | 条件调用: 如果 tsdf enabled → 走 TSDF, 否则走现有管线 |

### 2.3 engine.py 改动（约 30 行）

在 `_trigger()` 中，`fuse()` 之前插入：

```python
tsdf_cfg = config.get('reconstruction', {}).get('tsdf', {})
if tsdf_cfg.get('enabled', False):
    from server.reconstruction.surface import reconstruct_tsdf
    pc_url = reconstruct_tsdf(frames, positions, config)
else:
    # 现有管线: fuse → Poisson / _save_pointcloud
    ...
```

### 2.4 前端无需改动

TSDF 输出的 mesh 格式和 Poisson 一样（顶点+面索引），前端 `addToScene` 照常工作。

---

## 三、配置文件（config.yaml）

在 `reconstruction` 段新增：

```yaml
reconstruction:
  mode: "incremental"
  frame_threshold: 30
  voxel_size: 0.05
  tsdf:
    enabled: false         # 开启 TSDF 体素融合（和 surface 互斥）
    voxel_length: 0.05     # 体素分辨率 (m), 越小越精细、越吃内存
    sdf_trunc: 0.10        # 截断距离 (m), 通常 = voxel_length * 2

  surface:
    enabled: true          # Poisson 表面重建 (和 tsdf 互斥)
    ...
```

`tsdf.enabled` 和 `surface.enabled` **互斥**，engine 只走一个。

---

## 四、reconstruct_tsdf 伪代码

```python
def reconstruct_tsdf(frames, positions, config):
    """用 TSDF 体素融合替代 fuse + Poisson"""

    tsdf_cfg = config['reconstruction']['tsdf']
    voxel_size = tsdf_cfg['voxel_length']
    sdf_trunc = tsdf_cfg['sdf_trunc']

    manager = TSDFManager(voxel_size, sdf_trunc)

    # 逐帧: 深度图 → 点云 → 世界坐标 → 积分进体素
    for frame, pose in zip(frames, positions):
        pc = depth_to_pointcloud(frame.depth_map)
        pc_vehicle = _camera_to_vehicle(pc)
        pc_world = _vehicle_to_world(pc_vehicle, pose)

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(pc_world)

        # 构造 4×4 位姿矩阵
        pose_mat = _pose_to_matrix(pose)
        manager.integrate(pcd, pose_mat)

    # 提取 mesh
    mesh = manager.extract_mesh()
    if len(mesh.vertices) == 0:
        return None

    # 写 PLY
    output_dir = config.get('output', {}).get('point_cloud_dir', 'output')
    os.makedirs(output_dir, exist_ok=True)
    filename = f"tsdf_{time.time():.0f}.ply"
    filepath = os.path.join(output_dir, filename)
    o3d.io.write_triangle_mesh(filepath, mesh)

    return f"/{output_dir}/{filename}"
```

---

## 五、内存估算

| 场景 | 体素分辨率 | 体素格数 (20m × 5m × 5m) | 内存 |
|------|-----------|--------------------------|------|
| 精细 | 0.02m | 1000×250×250 = 6250万 | ~500 MB |
| 中等 | 0.05m | 400×100×100 = 400万 | ~32 MB |
| 粗 | 0.10m | 200×50×50 = 50万 | ~4 MB |

建议从 **0.05m** 开始，32MB 压力很小。隧道窄长，体素范围可以用动态包围盒缩小。

---

## 六、潜在问题

1. **TSDF 需要相机 pose 矩阵（4×4）**：你们目前只有 (x, y, heading)，需要构造完整的旋转矩阵（roll/pitch 设 0）
2. **大场景体素内存**：长时间采集时不能无限扩大体素，需要滑动窗口或分块 TSDF
3. **marching cubes 在 CPU 上也慢**：百万级体素时可能需要 100-300ms，建议体素格控制在 100 万以内
4. **和 Poisson 互斥**：不能同时开，配置需校验

---

## 七、实施优先级

| 阶段 | 内容 | 时间 |
|------|------|------|
| P0 | `tsdf.py` + `config.yaml` + `engine.py` 基础接入 | 半天 |
| P1 | 位姿矩阵构造 + 测试 mock 数据 | 半天 |
| P2 | 动态包围盒（节省内存） | 半天 |
| P3 | 滑动窗口 TSDF（支持长时间采集） | 1 天 |
