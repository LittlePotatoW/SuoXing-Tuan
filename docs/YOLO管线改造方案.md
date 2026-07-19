# YOLO 检测管线改造方案

## 一、现状分析

### 当前管线（有问题）

```
push_frame → buffer.push → 攒到 frame_threshold → _trigger()
  _trigger():
    depth_to_pointcloud(无序 N×3) → map_frames → fuse → result_pc
    ── 然后批量跑 YOLO（❌ 问题在这里）──
    detector.detect() × 30帧 → apply_nms()
    map_to_3d(dets, result_pc, None)  ── 崩！result_pc 已融合，不是有序结构
```

**问题**：
1. `map_to_3d` 需要 (H,W,3) 有序点云（像素坐标 → 3D 映射），但此时点云已经 `map_frames` + `fuse` 变成无序 N×3
2. 30 帧攒一起跑 YOLO，CPU 上可能慢
3. 无论实时还是回放都跑 YOLO

### 当前数据可用性

深度相机能提供**逐像素深度**，精度远高于参考项目的 LiDAR 中位数深度。

`depth_to_pointcloud` 内部已解码深度图为 (H,W) 浮点数组，但只返回了 N×3 无序点云。有序结构被丢弃了。

## 二、参考项目对比

| 方面 | 参考项目 | 我们 |
|------|---------|------|
| YOLO 触发位置 | `upload_frame` 路由层，per-frame | `_trigger` 引擎层，攒批 |
| YOLO 设备 | GPU（三张 4090） | CPU |
| YOLO 速度 | <50ms/帧 | <50ms/帧（你已确认） |
| 深度来源 | LiDAR 点云 → 中位数深度（整张图一个值） | 深度相机 → **逐像素深度**（更精确） |
| 2D→3D 投影 | `projector.py` 针孔模型反算 | `postprocess.py` `map_to_3d` 裁剪有序点云 |
| 回放时跑 YOLO？ | 不跑！只重建点云 | 跑（这是我们回放慢的原因） |
| 线程模型 | `run_in_executor` 丢线程池 | 同步阻塞 |

### 参考项目关键代码

**实时模式**（`routes.py:81-117`）— YOLO per-frame：
```python
def _process():
    fused = fusion.process(frame)
    engine.add_frame(fused)
    if _inference_engine and _inference_engine.loaded:  # 有模型才跑
        _run_yolo_on_frame(frame, fused, engine)         # ← YOLO 在这里
    return engine.get_result()

result = await loop.run_in_executor(None, _process)      # 丢线程池
```

**回放模式**（`routes.py:197-207`）— 不跑 YOLO：
```python
def _process():
    fused = fusion.process(frame)
    engine.add_frame(fused)           # 只存点云
    return engine.get_result()        # ← 没有 _run_yolo_on_frame !
```

## 三、改造方案

### 核心思路

把 YOLO 从 `_trigger`（批量）移到 `push_frame`（per-frame），保留有序点云做 3D 映射。

### 3.1 修改 `depth_to_pointcloud` — 加有序输出

`backend/server/pointcloud/converter.py` 新增函数：

```python
def decode_depth(depth_b64: str) -> tuple[np.ndarray, np.ndarray] | None:
    """
    解码深度图，返回有序数据（给 map_to_3d 用）

    Returns:
        depth_m:   (H, W) float32 深度值(米)，含无效区域(0或超出范围)
        ordered_pc: (H, W, 3) float32 有序点云，无效区域为 NaN
        失败返回 None
    """
```

原有的 `depth_to_pointcloud` 内部改为调用此函数 + 提取有效点，不改接口。

### 3.2 修改引擎 — push_frame 时跑 YOLO

`backend/server/engine/engine.py`：

**`push_frame`**：新增参数或读取 `_yolo_enabled`，如果开启则 per-frame 跑 YOLO：

```python
def push_frame(self, frame_id, timestamp, image, depth_map):
    # 1. 解码深度图（拿有序结构）
    decoded = decode_depth(depth_map)
    if decoded:
        depth_m, ordered_pc = decoded

    # 2. YOLO per-frame（如果开启）
    if self._yolo_enabled and decoded:
        dets = detector.detect(image)                              # 2D 框
        dets = apply_nms(dets)                                      # 去重
        dets = map_to_3d(dets, ordered_pc, depth_m)                # 2D → 3D ✓
        self._pending_detections.extend(dets)                       # 暂存

    # 3. 现有逻辑：转无序点云 + 存 buffer
    pc = depth_to_pointcloud(depth_map)                            # N×3 无序
    entry = FrameEntry(frame_id, timestamp, image, depth_map, pc)  # 加 pc 字段
    self._buffer.push(entry)
    if self._buffer.is_ready():
        self._trigger()
```

**`_trigger`**：不再跑 YOLO，直接收集已存好的检测结果：

```python
def _trigger(self):
    with self._engine_lock:
        frames = self._buffer.flush()
        ...
        # 收集 per-frame 已跑好的检测结果（带 center_3d）
        detections = list(self._pending_detections)
        self._pending_detections.clear()
```

### 3.3 回放时关闭 YOLO

`frontend/src/views/ReplayModeling.vue`：

```ts
await resetReconstruction({
    mode: reconDefaults.mode,
    frame_threshold: reconDefaults.frame_threshold,
    voxel_size: reconDefaults.voxel_size,
    yolo_enabled: false,  // ← 回放不跑 YOLO，只做点云重建
})
```

### 3.4 FrameEntry 扩展

`backend/server/engine/frame_buffer.py` 的 `FrameEntry` 加 `point_cloud` 字段（预计算的 N×3 无序点云），_trigger 里直接用，避免二次解码。

## 四、不改的

- 引擎整体架构（buffer → trigger → map_frames → fuse → PLY）
- 位置估计器
- 前端轮询逻辑
- `map_to_3d` 实现（已经正确，只是调用位置错了）

## 五、改造后的数据流

```
push_frame(image, depth_map):
  ├─ decode_depth(depth_map) → ordered_pc (H,W,3) + depth_m (H,W)
  ├─ [YOLO ON] detect(image) → 2D boxes
  ├─ [YOLO ON] apply_nms(boxes)
  ├─ [YOLO ON] map_to_3d(boxes, ordered_pc, depth_m) → 3D centers ✓
  ├─ depth_to_pointcloud(depth_map) → pc (N,3) 无序
  └─ buffer.push(FrameEntry(..., pc, dets))

_trigger():
  ├─ 遍历 frames:
  │   ├─ 直接用 frame.pc（无序点云，已预计算）
  │   └─ get_position_at() → pose
  ├─ map_frames(pcs, poses)
  ├─ fuse(merged, previous)
  ├─ 收集所有 frame 的 dets（已带 center_3d）
  ├─ save PLY
  └─ _latest_result.detections = dets ✓
```

## 六、优势

- `map_to_3d` 用我们深度图的**逐像素深度**，比参考 LiDAR 中位数更精准
- per-frame 不攒批，实时模式下不阻塞
- 回放时 `yolo_enabled: false`，不跑检测只重建，快
- 深度图只解码一次（`decode_depth` → 有序给 YOLO，无序给重建）
