# 多模态工业缺陷检测模型 — 架构设计

## 1. 整体概览

模型命名为 **AnyModality-DETR**，由四大子系统构成：

| 子系统 | 功能 | 是否依赖特定模态 |
|--------|------|:---:|
| 模态编码器组 | 将原始数据转为统一 token 序列 | 是（每种模态一个独立编码器） |
| 模态感知融合层 | 接收任意数量/组合的 token 序列，输出融合 token | 否 |
| 共享 Transformer 解码器 | Object-query 方式从融合 token 中解码缺陷 | 否 |
| 多任务检测头 | 输出缺陷类别、边界框、分割 mask | 否 |

**关键约束**：融合层和解码器完全不知道输入来自什么模态，只看到 token 序列。这保证了任意模态组合都能工作。

---

## 2. 训练网络 — 完整层级结构

训练时网络包含所有模块。根据每个样本实际拥有的模态，部分路径可能被跳过。

### 2.1 RGB 图像编码器（RGB Encoder）

**基础骨干：EfficientNet-B0**（从 `timm` 加载预训练权重）

```
输入层:
  └── raw_rgb: (B, 3, 640, 640) float32, 归一化后 [mean=0.485,0.456,0.406, std=0.229,0.224,0.225]

EfficientNet-B0 特征提取（冻结 stem + stage1，可训练 stage2+）:
  
  Stem (stage0):
    ├── Conv2d(3→32, k=3, s=2, p=1) + BN + SiLU        → (B, 32, 320, 320)
    
  Stage1 (MBConv1, k3×3, SE: 4):
    ├── MBConv(32→16, expand=1, k=3, s=1, SE_ratio=4)   → (B, 16, 320, 320)   ← 冻结
  
  Stage2 (MBConv6, k3×3, SE: 4):
    ├── MBConv(16→24, expand=6, k=3, s=2, SE_ratio=4)   → (B, 24, 160, 160)   ← 可训练
    ├── MBConv(24→24, expand=6, k=3, s=1, SE_ratio=4)   → (B, 24, 160, 160)
  
  Stage3 (MBConv6, k5×5, SE: 4):
    ├── MBConv(24→40, expand=6, k=5, s=2, SE_ratio=4)   → (B, 40,  80,  80)   ← 可训练
    ├── MBConv(40→40, expand=6, k=5, s=1, SE_ratio=4)   → (B, 40,  80,  80)
  
  Stage4 (MBConv6, k3×3, SE: 4):
    ├── MBConv(40→80, expand=6, k=3, s=2, SE_ratio=4)   → (B, 80,  40,  40)   ← 可训练
    ├── MBConv(80→80, expand=6, k=3, s=1, SE_ratio=4)   → (B, 80,  40,  40)
  
  Stage5 (MBConv6, k5×5, SE: 4):
    ├── MBConv(80→112, expand=6, k=5, s=1, SE_ratio=4)   → (B, 112, 40,  40)  ← 可训练
    ├── MBConv(112→112, expand=6, k=5, s=1, SE_ratio=4)  → (B, 112, 40,  40)
  
  Stage6 (MBConv6, k5×5, SE: 4):
    ├── MBConv(112→192, expand=6, k=5, s=2, SE_ratio=4)  → (B, 192, 20,  20)  ← 可训练
    ├── MBConv(192→192, expand=6, k=5, s=1, SE_ratio=4)  → (B, 192, 20,  20)
    ├── MBConv(192→192, expand=6, k=5, s=1, SE_ratio=4)  → (B, 192, 20,  20)
    ├── MBConv(192→192, expand=6, k=5, s=1, SE_ratio=4)  → (B, 192, 20,  20)
    
  Stage7 (MBConv6, k3×3, SE: 4):
    ├── MBConv(192→320, expand=6, k=3, s=1, SE_ratio=4)  → (B, 320, 20,  20)  ← 可训练

多尺度特征输出（选取 3 个尺度）:
  ├── C3 = Stage3 输出: (B, 40,  80, 80)   — 高分辨率，检测小缺陷
  ├── C4 = Stage5 输出: (B, 112, 40, 40)   — 中分辨率
  ├── C5 = Stage7 输出: (B, 320, 20, 20)   — 低分辨率，检测大缺陷
```

**特征投影到统一维度（d_model = 256）**：

```
多尺度投影层:
  ├── Proj_C3: Conv2d(40→256,  k=1)             → (B, 256, 80, 80)
  ├── Proj_C4: Conv2d(112→256, k=1)             → (B, 256, 40, 40)
  ├── Proj_C5: Conv2d(320→256, k=1)             → (B, 256, 20, 20)

扁平化为 token 序列:
  ├── C3_flatten: (B, 256, 80, 80) → reshape → (B, 6400, 256)   # 6400 = 80×80
  ├── C4_flatten: (B, 256, 40, 40) → reshape → (B, 1600, 256)   # 1600 = 40×40
  ├── C5_flatten: (B, 256, 20, 20) → reshape → (B,  400, 256)   #  400 = 20×20

合并所有尺度的 token:
  └── rgb_tokens = Concat(C3+C4+C5, dim=1)       → (B, 8400, 256)

加上 2D 位置编码:
  └── pos_embed_2d: 可学习参数 (1, 8400, 256)
  └── rgb_tokens = rgb_tokens + pos_embed_2d      → (B, 8400, 256)
```

**参数量**：EfficientNet-B0 约 4.0M（冻结 stem+stage1 减半） + 投影层约 0.1M = **~4.1M**

---

### 2.2 点云编码器（Point Cloud Encoder）

**自建轻量 PointNet++ 风格编码器**（3 层 Set Abstraction，无 Feature Propagation）

```
输入层:
  └── raw_pc: (B, 8192, 3) float32 [XYZ 坐标，已归一化到 [-1, 1]]

-------- 第 1 层 Set Abstraction (SA1) --------
  
  FPS 采样:
    ├── 从 8192 个点中采样 1024 个中心点
    └── xyz_centers1: (B, 1024, 3)
  
  Ball Query (半径 r=0.1, 每组最多 32 个点):
    ├── 为每个中心点找半径 0.1 内的邻域点
    └── grouped_points: (B, 1024, 32, 3)
  
  Mini-PointNet (共享 MLP — 对每个组的 32 个点独立处理):
    ├── Conv1d(3+3 → 64, k=1)    输入: (B, 1024, 32, 6)   ← (坐标 + 相对坐标)
    │       + BN + ReLU                           → (B, 1024, 32, 64)
    ├── Conv1d(64 → 64, k=1)
    │       + BN + ReLU                           → (B, 1024, 32, 64)
    ├── Conv1d(64 → 128, k=1)
    │       + BN + ReLU                           → (B, 1024, 32, 128)
    └── MaxPool across 32 points                  → (B, 1024, 128)
  
  SA1 输出:
    └── pc_feat1: (B, 1024, 128),   xyz1: (B, 1024, 3)


-------- 第 2 层 Set Abstraction (SA2) --------
  
  FPS 采样:
    ├── 从 1024 个点中采样 256 个中心点
    └── xyz_centers2: (B, 256, 3)
  
  Ball Query (半径 r=0.2, 每组最多 32 个点):
    ├── 输入 xyz1=(B,1024,3), xyz_centers2=(B,256,3)
    └── grouped_points: (B, 256, 32, 3)
    └── grouped_feats:  (B, 256, 32, 128)   ← 从 pc_feat1 中按索引取
  
  Mini-PointNet:
    ├── 拼接坐标和特征: (B, 256, 32, 3+3+128) = (B, 256, 32, 134)
    ├── Conv1d(134 → 128, k=1) + BN + ReLU     → (B, 256, 32, 128)
    ├── Conv1d(128 → 128, k=1) + BN + ReLU     → (B, 256, 32, 128)
    ├── Conv1d(128 → 256, k=1) + BN + ReLU     → (B, 256, 32, 256)
    └── MaxPool across 32 points                → (B, 256, 256)
  
  SA2 输出:
    └── pc_feat2: (B, 256, 256),   xyz2: (B, 256, 3)


-------- 第 3 层 Set Abstraction (SA3) --------
  
  FPS 采样:
    ├── 从 256 个点中采样 64 个中心点
    └── xyz_centers3: (B, 64, 3)
  
  Ball Query (半径 r=0.4, 每组最多 32 个点):
    ├── 输入 xyz2=(B,256,3), xyz_centers3=(B,64,3)
    └── grouped_points: (B, 64, 32, 3)
    └── grouped_feats:  (B, 64, 32, 256)
  
  Mini-PointNet:
    ├── 拼接: (B, 64, 32, 3+3+256) = (B, 64, 32, 262)
    ├── Conv1d(262 → 256, k=1) + BN + ReLU     → (B, 64, 32, 256)
    ├── Conv1d(256 → 256, k=1) + BN + ReLU     → (B, 64, 32, 256)
    ├── Conv1d(256 → 256, k=1) + BN + ReLU     → (B, 64, 32, 256)
    └── MaxPool across 32 points                → (B, 64, 256)
  
  SA3 输出:
    └── pc_feat3: (B, 64, 256),   xyz3: (B, 64, 3)

-------- 最终点云 token --------
  
  将 SA3 输出作为点云 token 序列:
    └── pc_tokens = pc_feat3                      → (B, 64, 256)
  
  加上 3D 位置编码 (用 xyz3 坐标做正弦编码):
    ├── pos_embed_3d = SinusoidalEncoding(xyz3)    → (B, 64, 256)
    └── pc_tokens = pc_tokens + pos_embed_3d       → (B, 64, 256)
```

**参数量**：3 层 SA 中各 MLP 卷积的总和，约 **~2.0M**

**设计说明**：
- 3 层 SA 将 8192 点 → 1024 → 256 → 64 个 token，每个 token 编码了不同感受野的局部几何信息
- 最终 64 个 token 对应点云中 64 个关键区域，维度 256 与 RGB token 维度一致
- 不使用 Feature Propagation（FP）层因为我们只需要全局特征，不需要逐点分割

---

### 2.3 模态感知融合层（Modality-Aware Fusion Layer）

这是整个架构中负责处理"模态不确定"的核心模块。输入可以是 1 个或 2 个 token 序列。

```
融合层输入:
  ├── rgb_tokens: (B, 8400, 256) 或 None  (None 表示该模态缺失)
  └── pc_tokens:  (B, 64, 256)   或 None

-------- Step 1: Missing Token 替换 --------

可学习参数:
  ├── missing_rgb_token: (1, 1, 256)   ← 训练时学习
  └── missing_pc_token:  (1, 1, 256)   ← 训练时学习

当 rgb_tokens = None 时:
  └── rgb_tokens = missing_rgb_token.expand(B, 1, 256)   → (B, 1, 256)

当 pc_tokens = None 时:
  └── pc_tokens = missing_pc_token.expand(B, 1, 256)     → (B, 1, 256)

保证经过 Step1 后两个 token 序列都"存在"（至少有一个占位 token）

-------- Step 2: 模态类型注入 --------

可学习参数:
  ├── modality_type_embed: Embedding(2, 256)
  │     索引 0 → "RGB type"  embedding
  │     索引 1 → "PointCloud type" embedding
  └── (训练时学习，让模型区分 token 来源)

  ├── rgb_tokens = rgb_tokens + modality_type_embed(0)   → (B, N_rgb, 256)
  ├── pc_tokens  = pc_tokens  + modality_type_embed(1)   → (B, N_pc,  256)
  └── 注: 如果某模态缺失（N=1），那个唯一的 token 也被标记为对应类型

-------- Step 3: Token 拼接 --------

  ├── all_tokens = Concat([rgb_tokens, pc_tokens], dim=1)
  └── 总 token 数: N_rgb + N_pc
      - 两者都有: 8400 + 64 = 8464
      - 只有 RGB:  8400 + 1  = 8401
      - 只有 PC:   1 + 64    = 65

-------- Step 4: 自注意力融合（Fusion Transformer） --------

结构: 2 层标准 TransformerEncoderLayer

第 1 层融合:
  ├── MultiheadAttention (d_model=256, nhead=8, dropout=0.1)
  │     Q=all_tokens, K=all_tokens, V=all_tokens        → (B, N_total, 256)
  ├── Add & LayerNorm
  ├── FFN (dim_feedforward=512):
  │     Linear(256 → 512) + ReLU + Dropout(0.1)
  │     Linear(512 → 256) + Dropout(0.1)                → (B, N_total, 256)
  └── Add & LayerNorm                                   → (B, N_total, 256)

第 2 层融合（结构同第 1 层）:
  ├── MultiheadAttention (8 heads)
  ├── Add & LayerNorm
  ├── FFN (512)
  └── Add & LayerNorm                                   → (B, N_total, 256)

-------- Step 5: 模态门控（可选，推荐启用） --------

可学习参数:
  ├── rgb_gate: (1,)  初始化为 1.0
  └── pc_gate:  (1,)  初始化为 1.0

  ├── 按模态拆分 fused_tokens:
  │     fused_rgb_tokens = fused_tokens[:, :N_rgb, :] * sigmoid(rgb_gate)
  │     fused_pc_tokens  = fused_tokens[:, N_rgb:, :] * sigmoid(pc_gate)
  └── fused_tokens = Concat([fused_rgb_tokens, fused_pc_tokens], dim=1)

融合层输出:
  └── fused_tokens: (B, N_total, 256)
      N_total = 8400~8464 (取决于输入模态)
```

**参数量**：Missing tokens (2×256) + Type Embedding (2×256) + 2×TransformerEncoderLayer (~1.6M) + Gates (2) = **~1.6M**

**关键设计说明**：
- Step1-2 保证无论多少模态输入，都形成统一格式的 token 序列
- Step4 的自注意力让每个 token 可以关注任何其他 token（跨模态 + 同模态），当某个模态缺失时，对应位置只有一个占位 token，注意力自然集中在可用模态上
- Step5 的模态门控是可选的轻量调节机制，让模型学习"当前场景下哪个模态更可靠"

---

### 2.4 共享 Transformer 解码器（Shared Decoder）

DETR 风格的 query-based 解码器。完全不感知输入来自什么模态。

```
解码器输入:
  ├── fused_tokens:  (B, N_total, 256)   ← 来自融合层
  └── (无其他输入)

-------- 可学习的 Object Queries --------

  ├── query_embed: (50, 256)   ← 50 个可学习的 query 向量
  └── 初始化: nn.Embedding(50, 256)，随机初始化

-------- Decoder Layer 1 --------

  Self-Attention (query 之间的交互):
    ├── MultiheadAttention (d_model=256, nhead=8)
    │     Q=queries, K=queries, V=queries   → (B, 50, 256)
    │     query 之间学习不重叠，避免重复检测同一缺陷
    ├── Add & LayerNorm

  Cross-Attention (query 从 fused_tokens 中提取信息):
    ├── MultiheadAttention (d_model=256, nhead=8)
    │     Q=queries, K=fused_tokens, V=fused_tokens   → (B, 50, 256)
    │     每个 query 学习关注 fused_tokens 中与缺陷相关的区域
    ├── Add & LayerNorm

  FFN:
    ├── Linear(256 → 512) + ReLU + Dropout(0.1)
    ├── Linear(512 → 256) + Dropout(0.1)              → (B, 50, 256)
    └── Add & LayerNorm                                → (B, 50, 256)

-------- Decoder Layer 2 --------

  Self-Attention → Cross-Attention → FFN   (结构同上)
  
  输出: decoder_output: (B, 50, 256)
```

**参数量**：2×(Self-Attn + Cross-Attn + FFN) ≈ **~1.2M**

**设计说明**：
- 50 个 query 意味着最多检测 50 个缺陷（工业场景通常远少于这个数）
- Self-Attention + Cross-Attention 的经典 DETR 结构，query 在自注意力中去重，在交叉注意力中从图像/点云特征中提取缺陷信息
- 如果推理时需要更多 query，只需扩展 `query_embed` 参数量

---

### 2.5 多任务检测头（Detection Heads）

3 个并行的 FFN 头，从同一个 decoder 输出中预测不同内容。

```
输入: decoder_output: (B, 50, 256)

-------- 分类头 (Class Head) --------

  ├── Linear(256 → 256) + ReLU
  ├── Linear(256 → num_classes + 1)     # +1 = "无缺陷/背景"
  └── class_logits: (B, 50, num_classes+1)
      训练时用 FocalLoss(α=0.25, γ=2.0)
      标签分配用匈牙利匹配 (Hungarian Matching)

-------- 边界框头 (BBox Head) --------

  ├── Linear(256 → 256) + ReLU
  ├── Linear(256 → 256) + ReLU
  ├── Linear(256 → 4)                   # cx, cy, w, h (归一化 0~1)
  └── bbox_preds: (B, 50, 4)
      训练时用 GIoU Loss + L1 Loss (权重 2:1)

-------- 分割头 (Mask Head) — 可选 --------

  ├── 输入: decoder_output + fused_tokens 中对应的高分辨率部分
  ├── Linear(256 → 256) + ReLU
  ├── Linear(256 → H/4 × W/4)            # 粗粒度分割 mask
  ├── Reshape: (B, 50, H/4, W/4)
  └── mask_preds: (B, 50, 40, 40)        # 当输入 640×640 时，下采样 16×
      训练时用 Dice Loss + BCE Loss (权重 1:1)
      只在有 mask 标注时计算此 loss
```

**参数量**：Class Head (~0.07M) + BBox Head (~0.13M) + Mask Head (~0.07M) ≈ **~0.27M**

---

### 2.6 训练 Loss 汇总

```
总 Loss = L_det + α · L_distill + β · L_consistency

L_det (检测 loss，对所有样本计算):
  ├── L_class = FocalLoss(class_logits, matched_labels)
  ├── L_bbox  = GIoULoss(pred_bbox, gt_bbox) × 2 + L1Loss(pred_bbox, gt_bbox)
  ├── L_mask  = DiceLoss(pred_mask, gt_mask) + BCELoss(pred_mask, gt_mask) [可选]
  └── L_det = L_class + L_bbox + L_mask

L_distill (交叉模态蒸馏 loss，仅当双模态样本存在时计算):
  ├── L_distill_rgb = CosineSimilarityLoss(project_rgb(rgb_tokens), fused_tokens.detach())
  ├── L_distill_pc  = CosineSimilarityLoss(project_pc(pc_tokens), fused_tokens.detach())
  └── L_distill = L_distill_rgb + L_distill_pc
  
  其中 project_rgb 和 project_pc 是两个单层 Linear(256→256)

L_consistency (模态一致性 loss，仅当双模态样本存在时计算):
  ├── rgb_only_output = Decoder(Fusion(rgb_tokens, None))  ← 模拟只有 RGB 的推理路径
  ├── pc_only_output  = Decoder(Fusion(None, pc_tokens))   ← 模拟只有 PC 的推理路径
  ├── both_output     = Decoder(Fusion(rgb_tokens, pc_tokens))  ← 真实融合路径
  ├── L_cons_rgb = KLDivLoss(rgb_only_output.class_logits, both_output.class_logits.detach())
  ├── L_cons_pc  = KLDivLoss(pc_only_output.class_logits,  both_output.class_logits.detach())
  └── L_consistency = L_cons_rgb + L_cons_pc

超参数:
  ├── α (蒸馏权重): 默认 0.3
  ├── β (一致性权重): 默认 0.1
  └── 匈牙利匹配 cost: class_cost=1, bbox_cost=5, giou_cost=2
```

---

### 2.7 训练网络总参数量

| 模块 | 参数量 |
|------|:------:|
| RGB Encoder (EfficientNet-B0, 投影层) | ~4.1M |
| Point Cloud Encoder (PointNet++ 3层SA) | ~2.0M |
| Modality-Aware Fusion Layer | ~1.6M |
| Shared Transformer Decoder | ~1.2M |
| Detection Heads | ~0.27M |
| 蒸馏投影层 (project_rgb, project_pc) | ~0.13M |
| **总计** | **~9.3M** |

ONNX 导出后约 **35-40MB** (FP32)，INT8 量化后约 **10MB**。

---

## 3. 推理网络 — 三种推理路径

推理时，根据可用模态选择对应路径。**核心思想**：无论走哪条路径，decoder 和 detection head 的输入格式完全一致，因此可以共享。

### 3.1 路径 A：仅 RGB 图像

```
raw_rgb (3, 640, 640)
  │
  ▼
RGB Encoder (EfficientNet-B0 + 投影)
  │
  ▼
rgb_tokens (8400, 256)
  │
  ▼
Fusion Layer (pc=None, 使用 missing_pc_token)
  ├── Missing Token: pc_tokens ← (1, 256)
  ├── Type Embedding: rgb=type0, pc=type1
  ├── 2× Self-Attention (8401 tokens)
  └── Modality Gate: rgb_gate→1, pc_gate→0
  │
  ▼
fused_tokens (8401, 256)
  │
  ▼
Shared Decoder (2 layers, 50 queries)
  │
  ▼
decoder_output (50, 256)
  │
  ▼
Detection Heads
  ├── class_logits (50, C+1)
  ├── bbox_preds  (50, 4)
  └── mask_preds  (50, 40, 40) [可选]
```

### 3.2 路径 B：仅点云

```
raw_pc (8192, 3)
  │
  ▼
Point Cloud Encoder (3层 SA)
  │
  ▼
pc_tokens (64, 256)
  │
  ▼
Fusion Layer (rgb=None, 使用 missing_rgb_token)
  ├── Missing Token: rgb_tokens ← (1, 256)
  ├── Type Embedding: rgb=type0, pc=type1
  ├── 2× Self-Attention (65 tokens)
  └── Modality Gate: rgb_gate→0, pc_gate→1
  │
  ▼
fused_tokens (65, 256)
  │
  ▼
Shared Decoder (2 layers, 50 queries)
  │
  ▼
decoder_output (50, 256)
  │
  ▼
Detection Heads
  ├── class_logits (50, C+1)
  ├── bbox_preds  (50, 4)
  └── mask_preds  (50, 40, 40) [可选]
```

**注意**：这个路径输出的是 2D bbox（在哪个坐标系？）
- 如果点云和图像经过 2D-3D 标定（已知相机内参外参），bbox 可以直接投影到 2D 图像平面
- 如果没有标定，bbox 定义在点云的 XY 投影面上

### 3.3 路径 C：RGB + 点云（两者都有）

```
raw_rgb (3, 640, 640)          raw_pc (8192, 3)
  │                               │
  ▼                               ▼
RGB Encoder                  PC Encoder
  │                               │
  ▼                               ▼
rgb_tokens (8400, 256)       pc_tokens (64, 256)
  │                               │
  └───────────┬───────────────────┘
              ▼
Fusion Layer (两者都有)
  ├── 无 Missing Token 替换
  ├── Type Embedding: 各自加对应类型标记
  ├── 2× Self-Attention (8464 tokens, 跨模态交互)
  └── Modality Gate: 根据训练学到的权重调节
  │
  ▼
fused_tokens (8464, 256)
  │
  ▼
Shared Decoder (2 layers, 50 queries)
  │
  ▼
decoder_output (50, 256)
  │
  ▼
Detection Heads
  ├── class_logits (50, C+1)
  ├── bbox_preds  (50, 4)
  └── mask_preds  (50, 40, 40) [可选]
```

### 3.4 三种路径对比

| 特性 | 路径 A (RGB only) | 路径 B (PC only) | 路径 C (RGB+PC) |
|------|:---:|:---:|:---:|
| 输入 token 数 | 8401 | 65 | 8464 |
| 推理速度 (相对) | 1.0× (最快) | 1.5× (编码器快但 decoder token 少) | 0.7× (最慢) |
| 检测精度 (预期) | 基线 | 略低于 RGB | 最高 |
| 适合检测的缺陷类型 | 颜色/纹理缺陷、表面划痕 | 形变/几何缺陷、凹陷 | 全部类型 |
| 需要的传感器 | 工业相机 | 激光雷达/深度相机 | 两者都需要 |

### 3.5 推理只用一个模型

三种推理路径共享**同一套权重**。不需要为每种模态组合训练/存储单独的模型。这是通过以下机制实现的：

1. **独立编码器**：每个模态有自己的编码器，推理时按需激活
2. **Missing Token**：缺失的模态被替换为训练中学到的占位 token
3. **共享 Decoder + Head**：完全模态无关，接受任何 token 序列作为输入

实际部署时，可以：
- 导出一个完整模型（包含所有编码器），推理时动态分支
- 或者导出 3 个子模型（分别去掉不需要的编码器），根据场景加载对应的 ONNX

---

## 4. 前后处理管线

### 4.1 前处理详细规格

```
┌──────────────────────────────────────────────────────────────┐
│                     RGB 图像前处理                            │
│                                                              │
│  原始输入: 工业相机抓帧, 通常 1920×1080 或 2448×2048          │
│                                                              │
│  Step 1 — 缩放:                                              │
│    Resize 短边到 640, 保持长宽比                             │
│    例如: 1920×1080 → 1138×640                               │
│                                                              │
│  Step 2 — 中心裁剪或 Padding:                                │
│    CenterCrop 或 Pad 到 640×640                              │
│    最终: (640, 640, 3)                                       │
│                                                              │
│  Step 3 — 归一化:                                            │
│    RGB → float32 [0, 1]                                     │
│    减均值: [0.485, 0.456, 0.406]                            │
│    除标准差: [0.229, 0.224, 0.225]                           │
│    最终: (3, 640, 640) float32                               │
│                                                              │
│  Step 4 — (仅训练时) 数据增强:                                │
│    随机水平翻转 p=0.5                                        │
│    随机旋转 ±15°                                             │
│    亮度/对比度/饱和度抖动 ±20%                                │
│    高斯噪声 σ=0.01                                           │
│    CutOut 随机遮挡 10% 区域                                   │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                     点云前处理                                │
│                                                              │
│  原始输入: 激光雷达或深度传感器, N 个点 (1000 ~ 100000+)       │
│                                                              │
│  Step 1 — 坐标归一化:                                        │
│    如果点云单位不是米，转为米                                │
│    (例如毫米 → 除以 1000)                                    │
│                                                              │
│  Step 2 — RANSAC 背景平面去除:                                │
│    open3d.geometry.PointCloud.segment_plane(                  │
│        distance_threshold=0.005,  # 5mm 内算平面             │
│        ransac_n=3,                                             │
│        num_iterations=1000                                     │
│    )                                                         │
│    去除平面上的点（工作台），保留物体上的点                    │
│    输出: N' 个前景点                                         │
│                                                              │
│  Step 3 — 统计离群点去除:                                     │
│    open3d.geometry.PointCloud.remove_statistical_outlier(      │
│        nb_neighbors=20,                                        │
│        std_ratio=2.0                                           │
│    )                                                         │
│    去除孤立的噪声点                                           │
│    输出: N'' 个有效点                                         │
│                                                              │
│  Step 4 — FPS 降采样到固定点数:                               │
│    如果 N'' > 8192: FPS 采样 8192 个点                       │
│    如果 N'' < 8192: 随机重复点到 8192                         │
│    输出: (8192, 3)                                            │
│                                                              │
│  Step 5 — 中心化 + 归一化:                                    │
│    减去点云质心 (centering)                                   │
│    除以最大 Euclidean 距离 (scaling to [-1, 1])              │
│    最终: (8192, 3) float32                                    │
│                                                              │
│  Step 6 — (仅训练时) 数据增强:                                │
│    随机绕 Z 轴旋转 ±30°                                      │
│    随机平移 ±2% 范围                                         │
│    随机缩放 ±5%                                              │
│    点云抖动: 每个点加高斯噪声 σ=0.005                         │
│    随机降采样到 80% 的点 (模拟稀疏扫描)                       │
│    (如果 RGB 也做了水平翻转，点云需要同步翻转，否则标定失效)   │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 后处理详细规格

```
┌──────────────────────────────────────────────────────────────┐
│                       后处理管线                              │
│                                                              │
│  输入: 模型原始输出                                            │
│    class_logits: (50, num_classes+1)                          │
│    bbox_preds:   (50, 4)   ← [cx, cy, w, h] 归一化 0~1      │
│    mask_preds:   (50, 40, 40) [可选]                          │
│                                                              │
│  Step 1 — Softmax 分类:                                       │
│    class_probs = Softmax(class_logits, dim=-1)                │
│    取 max 概率的类别作为预测类别                              │
│    对应的概率值作为 confidence                                │
│                                                              │
│  Step 2 — 背景过滤:                                           │
│    过滤 class == "background" (最后一类)                      │
│    过滤 confidence < conf_threshold (默认 0.3)                │
│    输出: M 个有效检测 (M ≤ 50)                                │
│                                                              │
│  Step 3 — BBox 坐标反归一化:                                  │
│    [cx, cy, w, h] (归一化) → [x1, y1, x2, y2] (像素坐标)    │
│    x1 = (cx - w/2) × img_width                               │
│    y1 = (cy - h/2) × img_height                              │
│    x2 = (cx + w/2) × img_width                               │
│    y2 = (cy + h/2) × img_height                              │
│    如果原始图像经过 resize/pad, 需要反映射回原始尺寸           │
│                                                              │
│  Step 4 — NMS (非极大值抑制):                                  │
│    按 confidence 降序排列                                     │
│    IoU 阈值: 0.5 (缺陷通常不会严重重叠)                       │
│    输出: K 个最终检测 (K ≤ M)                                 │
│                                                              │
│  Step 5 — Mask 后处理 (如果有 mask head):                      │
│    取每个检测对应类别的 mask_preds                            │
│    Sigmoid 激活                                              │
│    二值化: threshold > 0.5                                    │
│    Resize 到原始图像尺寸                                      │
│    取 mask 的最小外接矩形作为精细化 bbox (可选)                │
│                                                              │
│  Step 6 — 3D 投影 (如果有点云 + 标定信息):                     │
│    利用相机内参 K 和外参 [R|t]                                │
│    将点云投影到图像平面                                       │
│    bbox 区域内对应的 3D 点 = 缺陷的 3D 位置                    │
│    输出: defect_3d_center, defect_3d_bbox                     │
│                                                              │
│  Step 7 — 结果打包:                                           │
│    [                                                          │
│      {                                                        │
│        "class": "scratch",                                    │
│        "confidence": 0.95,                                    │
│        "bbox_2d": [x1, y1, x2, y2],                           │
│        "bbox_3d": [x, y, z, dx, dy, dz],  # 可选              │
│        "mask": [[...]],                     # 可选             │
│      },                                                       │
│      ...                                                      │
│    ]                                                          │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. 数据流总览图

### 5.1 训练时数据流

```
                    ┌──────────────┐     ┌──────────────┐
                    │  Sample A    │     │  Sample B    │     │  Sample C    │
                    │  (只有RGB)   │     │  (只有点云)   │     │  (两者都有)  │
                    └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
                           │                    │                    │
                           ▼                    ▼                    ▼
                    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
                    │  RGB 前处理   │     │  点云前处理   │     │  RGB+PC前处理 │
                    └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
                           │                    │                    │
                           ▼                    ▼                    ▼
                    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
                    │  RGB Encoder │     │   PC Encoder │     │RGB Enc+PC Enc│
                    │  ↓           │     │   ↓           │     │   ↓      ↓   │
                    │  rgb_tokens  │     │   pc_tokens  │     │rgb_tok  pc_tok│
                    └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
                           │                    │                    │
                           ▼                    ▼                    ▼
                    ┌──────────────────────────────────────────────────┐
                    │           Modality-Aware Fusion Layer            │
                    │                                                  │
                    │  Sample A: rgb_tokens + missing_pc_token         │
                    │  Sample B: missing_rgb_token + pc_tokens         │
                    │  Sample C: rgb_tokens + pc_tokens               │
                    │            ↓                                     │
                    │        fused_tokens                              │
                    └──────────────────────┬───────────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────────┐
                    │           Shared Transformer Decoder             │
                    │           50 queries × 2 layers                  │
                    │                  ↓                               │
                    │            decoder_output (B, 50, 256)           │
                    └──────────────────────┬───────────────────────────┘
                                           │
                          ┌────────────────┼────────────────┐
                          ▼                ▼                ▼
                    ┌──────────┐    ┌──────────┐    ┌──────────┐
                    │Class Head│    │BBox Head │    │Mask Head │
                    └────┬─────┘    └────┬─────┘    └────┬─────┘
                         │              │              │
                         ▼              ▼              ▼
                    class_logits   bbox_preds    mask_preds
                         │              │              │
                         └──────────────┼──────────────┘
                                        │
                                        ▼
                    ┌──────────────────────────────────────────────┐
                    │                 Loss 计算                     │
                    │                                              │
                    │  所有样本: L_det                              │
                    │  只有 Sample C: L_distill + L_consistency     │
                    └──────────────────────────────────────────────┘
```

### 5.2 推理时数据流

```
                    实际可用模态
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     只有 RGB        只有点云       两者都有
          │              │              │
          ▼              ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │RGB Encoder│  │PC Encoder│  │RGB+PC Enc│
    └────┬─────┘  └────┬─────┘  └────┬─────┘
         │             │             │
         ▼             ▼             ▼
    ┌────────────────────────────────────────┐
    │    Fusion Layer (自动处理缺失模态)       │
    │    Missing Token + Type Embedding       │
    └──────────────────┬─────────────────────┘
                       │
                       ▼
    ┌────────────────────────────────────────┐
    │    Shared Decoder (2 layers, 50 queries)│
    └──────────────────┬─────────────────────┘
                       │
                       ▼
    ┌────────────────────────────────────────┐
    │         Detection Heads (3 FFN)        │
    └──────────────────┬─────────────────────┘
                       │
                       ▼
    ┌────────────────────────────────────────┐
    │              后处理管线                  │
    │  Softmax → 过滤 → 反归一化 → NMS → 打包  │
    └──────────────────┬─────────────────────┘
                       │
                       ▼
                  检测结果 JSON
```

---

## 6. 可调节参数速查表

### 6.1 结构参数（影响模型容量和推理速度）

| 参数 | 默认值 | 范围 | 调节效果 |
|------|:---:|------|---------|
| `d_model` | 256 | 128~512 | ↑ 更大 = 更强表达力 + 更多参数 |
| `num_queries` | 50 | 20~100 | ↑ 更多 = 可检测更多缺陷 + 稍慢 |
| `num_decoder_layers` | 2 | 1~4 | ↑ 更多 = 更强解码能力 + 更多参数 |
| `num_fusion_layers` | 2 | 1~3 | ↑ 更多 = 更强跨模态融合 |
| `nhead` (attention heads) | 8 | 4~8 | ↑ 更多 = 更丰富的注意力模式 |
| `ffn_dim` | 512 | 256~1024 | ↑ 更大 = FFN 更强 + 更多参数 |
| `rgb_backbone` | efficientnet_b0 | mobilenet_v3 / convnext_tiny | 精度 vs 速度权衡 |
| `N_points` (点云采样数) | 8192 | 2048~16384 | ↑ 更多 = 更精细几何 + 更慢 |
| `num_sa_layers` (SA 层数) | 3 | 2~4 | 点云编码器的感受野大小 |
| `sa_radius` (Ball Query 半径) | [0.1, 0.2, 0.4] | 按数据调整 | 控制局部邻域大小 |
| `use_mask_head` | True | True/False | 是否输出分割 mask |
| `use_modality_gate` | True | True/False | 是否使用模态门控 |

### 6.2 训练参数

| 参数 | 默认值 | 范围 | 调节效果 |
|------|:---:|------|---------|
| `lr` (学习率) | 1e-4 | 1e-5~5e-4 | 训练收敛速度与稳定性 |
| `lr_backbone` | 1e-5 | 1e-6~5e-5 | backbone 微调速度（一般设为主 lr 的 1/10） |
| `batch_size` | 8 | 2~32 | 受显存限制 |
| `α` (蒸馏权重) | 0.3 | 0.0~1.0 | ↑ 更大 = 单模态编码器更多从双模态样本学习 |
| `β` (一致性权重) | 0.1 | 0.0~0.5 | ↑ 更大 = 单模态推理结果更接近双模态 |
| `weight_decay` | 1e-4 | 1e-5~1e-3 | 正则化强度 |
| `dropout` | 0.1 | 0.0~0.3 | ↑ 更大 = 更强正则化（防止过拟合） |
| `clip_grad_norm` | 0.1 | 0.05~1.0 | 梯度裁剪阈值 |
| `warmup_epochs` | 5 | 1~20 | 学习率预热轮数 |
| `total_epochs` | 150 | 50~300 | 总训练轮数 |

### 6.3 损失函数中的可调参数

| 参数 | 默认值 | 范围 | 调节效果 |
|------|:---:|------|---------|
| FocalLoss `α` (正样本权重) | 0.25 | 0.1~0.5 | 平衡正负样本 |
| FocalLoss `γ` (聚焦参数) | 2.0 | 1.0~5.0 | ↑ 更大 = 更关注难分样本 |
| BBox Loss 中 GIoU : L1 权重比 | 2:1 | 1:1~5:1 | GIoU 侧重框的精确位置，L1 侧重坐标回归 |
| Mask Loss 中 Dice : BCE 权重比 | 1:1 | 1:1~5:1 | Dice 侧重重叠度，BCE 侧重逐像素精度 |
| 匈牙利匹配中 class:bbox:giou cost 比 | 1:5:2 | 按任务调整 | bbox cost 越大，匹配越看重位置准确性 |

### 6.4 推理参数

| 参数 | 默认值 | 范围 | 调节效果 |
|------|:---:|------|---------|
| `conf_threshold` | 0.3 | 0.1~0.9 | ↑ 更高 = 更少误检 + 更多漏检 |
| `nms_iou_threshold` | 0.5 | 0.3~0.7 | ↑ 更高 = 允许更多重叠检测 |
| `max_detections` | 50 | 10~100 | 单帧最大检测数（受 num_queries 限制） |
| `mask_threshold` | 0.5 | 0.3~0.7 | 分割 mask 二值化阈值 |

---

## 7. 训练与推理的差异对照

| 方面 | 训练 | 推理 |
|------|------|------|
| **数据流路径** | 根据样本模态动态分支 | 根据可用传感器动态分支 |
| **使用的模块** | 全部模块（编码器 + 融合 + 解码 + 头 + 蒸馏投影） | 减去蒸馏投影层 |
| **Loss 计算** | L_det + L_distill + L_consistency | 无需 loss，只前向传播 |
| **数据增强** | 开启（随机翻转/旋转/噪声等） | 关闭（保持输入原样） |
| **Dropout** | 开启（训练正则化） | 关闭（或等效于 scaling） |
| **BatchNorm** | 使用 batch 统计量 | 使用训练时累积的 running mean/std |
| **输出** | class_logits, bbox_preds, mask_preds (用于 loss) | 同上（用于后处理 → 最终结果） |
| **精度** | FP32 或 AMP (自动混合精度) | FP32 / FP16 / INT8 (取决于部署平台) |

---

## 8. 参考论文与层次结构对应关系

| 模块 | 参考论文 | 借用的设计 |
|------|---------|-----------|
| RGB Encoder 层级 | EfficientNet (Tan & Le, 2019) | MBConv 模块、SE 注意力、stage 划分 |
| Point Cloud Encoder 层级 | PointNet++ (Qi et al., 2017) | Set Abstraction (FPS + Ball Query + Mini-PointNet) |
| 点云增强 | Self-Attention PointNet++ (Procedia CIRP 2024) | SA 层中融入 Self-Attention 增强特征交互 |
| Fusion Layer (Missing Token) | AMBER (2025), DPMamba (IJCAI 2025) | 可学习的缺失模态 token 替代零填充 |
| Fusion Layer (Type Embedding) | SM3Det (2024) | 模态类型编码注入 token 序列 |
| Fusion Layer (Modality Gate) | ModalPatch (2025) | 不确定性引导的模态门控权重 |
| Shared Decoder | DETR (Carion et al., 2020) | Object Query + Self-Attn + Cross-Attn 结构 |
| 轻量 Decoder | RT-DETR (2024), SMT-DETR (2025) | 减少 decoder 层数、工业缺陷检测适配 |
| 交叉模态蒸馏 | CMDIAD (Information Fusion 2025) | 融合特征蒸馏到单模态编码器 |
| 模态一致性 | AnySeg (2025), Modality-Resilient IAD (2025) | KL 散度约束各模态路径输出一致 |
| 匈牙利匹配 | Deformable DETR (Zhu et al., 2020) | 训练时预测框与真值框的二分图匹配 |
| 点云预处理 | CFM (CVPR 2024), M3DM | RANSAC 背景去除 + FPS 采样标准流程 |

---

## 9. 从哪开始开发

```
Phase 1: 图像基线 (先跑通完整训练→推理 loop)
─────────────────────────────────────────────
  实现: RGB Encoder + Shared Decoder + Detection Heads
  跳过: PC Encoder, Fusion Layer (先用 Identity 占位)
  目标: 在纯图像数据上验证 DETR 检测范式可行
  验证: mAP 达到可用水平, 推理速度达标
  
Phase 2: 点云基线
─────────────────────────────────────────────
  实现: PC Encoder (PointNet++ 3层 SA)
  跳过: Fusion Layer (用 Identity 占位)
  目标: 在纯点云数据上验证点云检测可行
  验证: 点云检测精度与 RGB 检测可比
  
Phase 3: 双模态融合
─────────────────────────────────────────────
  实现: Modality-Aware Fusion Layer (含 Missing Token + Type Embedding + Self-Attention)
  目标: 用成对的双模态数据训练, 验证融合增益
  验证: 双模态 > 最佳单模态 ⩆ +3~5% mAP
  
Phase 4: 任意模态训练
─────────────────────────────────────────────
  实现: 混合 batch 训练 + 交叉蒸馏 + 一致性 loss
  目标: 不完整训练数据 → 完整推理能力
  验证: 各模态组合推理精度接近各模态单独训练的水平
  
Phase 5: 部署优化
─────────────────────────────────────────────
  实现: ONNX 导出 → TensorRT 优化 → backend/inference/ 集成
  目标: 边缘设备实时推理
  验证: Jetson Orin 上 >20 FPS
```
