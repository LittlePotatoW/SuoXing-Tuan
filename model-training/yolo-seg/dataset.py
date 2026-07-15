# ============================================================
# tunnel-defect-ml/dataset.py
# 数据格式转换 — 多种标注格式 → YOLOv8-seg 分割格式
#
# 支持的输入格式:
#   - mask png (像素级标注)  → polygon
#   - VOC xml (bbox)          → bbox
#   - COCO json               → polygon/bbox
#
# YOLOv8-seg 分割标注格式:
#   每张图对应同名 .txt, 每行一个实例:
#     class_id x1 y1 x2 y2 x3 y3 ...
#   坐标归一化到 0~1
# ============================================================

import cv2
import numpy as np
from pathlib import Path
import shutil
import yaml
import json
import random
from typing import Optional
from tqdm import tqdm


# ============================================================
# 核心转换函数
# ============================================================

def mask_to_polygon(mask_path: str, epsilon: float = 0.001,
                    min_area: int = 25) -> list:
    """
    mask png → YOLOv8-seg polygon 列表

    参数:
      mask_path: mask 图片路径 (灰度图, 非零=缺陷区域)
      epsilon:   轮廓近似精度 (占周长比例)
      min_area:  最小连通域面积 (过滤噪声)

    返回:
      [[x1,y1, x2,y2, ...], ...]  归一化 polygon 列表
      每个 polygon 代表一个独立缺陷实例
    """
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        return []

    h, w = mask.shape

    # 连通域分析 — 区分同一 mask 中的多个实例
    _, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)

    polygons = []
    for label_id in range(1, stats.shape[0]):
        if stats[label_id, cv2.CC_STAT_AREA] < min_area:
            continue

        instance_mask = (labels == label_id).astype(np.uint8) * 255
        contours, _ = cv2.findContours(instance_mask, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if len(cnt) < 3:
                continue
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon * peri, True)
            if len(approx) < 3:
                continue
            pts = (approx / [w, h]).reshape(-1).tolist()
            pts = [round(p, 6) for p in pts]
            polygons.append(pts)

    return polygons


def mask_to_bbox(mask_path: str, min_size: int = 3) -> list:
    """
    mask png → YOLO bbox 列表 (检测模式用)

    返回:
      [[cx, cy, w, h], ...]  归一化 bbox
    """
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None or mask.max() == 0:
        return []

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)
    bboxes = []
    h, w = mask.shape
    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw < min_size or bh < min_size:
            continue
        cx = (x + bw / 2) / w
        cy = (y + bh / 2) / h
        bboxes.append([cx, cy, bw / w, bh / h])
    return bboxes


# ============================================================
# 批量转换
# ============================================================

def convert_mask_dataset(
    image_dir: str,
    mask_dir: str,
    output_dir: str,
    class_map: dict = None,
    split: str = "train",
    mode: str = "seg",
):
    """
    批量转换 mask 数据集 → YOLO 格式

    参数:
      image_dir:  图片目录 (.jpg/.png)
      mask_dir:   mask 目录 (同名 png)
      output_dir: 输出根目录
      class_map:  像素值→类别映射, 如 {255: 0, 127: 1}
                  None 时所有非零值归为 class 0
      split:      train / val / test
      mode:       "seg" (分割/polygon) 或 "det" (检测/bbox)

    输出:
      {output_dir}/images/{split}/  图片
      {output_dir}/labels/{split}/  标注 .txt

    对标论文: Huang et al. (2025)
      class_map={255: 0, 128: 1, 64: 2}  # crack/leakage/spalling
    """
    if class_map is None:
        class_map = {255: 0}

    image_dir = Path(image_dir)
    mask_dir = Path(mask_dir)
    out_img = Path(output_dir) / "images" / split
    out_lbl = Path(output_dir) / "labels" / split
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    exts = ["*.jpg", "*.png", "*.JPG", "*.jpeg"]
    image_files = []
    for ext in exts:
        image_files.extend(image_dir.glob(ext))

    if not image_files:
        print(f"WARNING: {image_dir} 中未找到图片")
        return

    count = 0
    for img_path in tqdm(image_files, desc=f"Converting [{split}]"):
        # 找对应 mask
        mask_path = None
        for pattern in [f"{img_path.stem}.png", f"{img_path.stem}_mask.png",
                        f"{img_path.stem}_label.png"]:
            candidate = mask_dir / pattern
            if candidate.exists():
                mask_path = candidate
                break
        if mask_path is None:
            continue

        # 读 mask
        mask_img = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask_img is None or mask_img.max() == 0:
            continue

        all_lines = []

        for pixel_val, class_id in class_map.items():
            class_binary = np.where(mask_img == pixel_val, 255, 0).astype(np.uint8)
            tmp = out_lbl / f"_tmp_{img_path.stem}_c{class_id}.png"
            cv2.imwrite(str(tmp), class_binary)

            if mode == "seg":
                polygons = mask_to_polygon(str(tmp))
                for poly in polygons:
                    if len(poly) >= 6:
                        pts_str = " ".join(f"{p:.6f}" for p in poly)
                        all_lines.append(f"{class_id} {pts_str}\n")
            else:
                bboxes = mask_to_bbox(str(tmp))
                for bbox in bboxes:
                    all_lines.append(
                        f"{class_id} {bbox[0]:.6f} {bbox[1]:.6f} "
                        f"{bbox[2]:.6f} {bbox[3]:.6f}\n"
                    )
            tmp.unlink()

        if not all_lines:
            continue

        shutil.copy2(str(img_path), str(out_img / img_path.name))
        (out_lbl / f"{img_path.stem}.txt").write_text("".join(all_lines))
        count += 1

    print(f"  {split}: {count} 张有效图片")


def convert_voc_dataset(
    xml_dir: str,
    image_dir: str,
    output_dir: str,
    class_map: dict,
    split: str = "train",
):
    """
    VOC xml 标注 → YOLO bbox 格式
    """
    import xml.etree.ElementTree as ET

    xml_dir = Path(xml_dir)
    image_dir = Path(image_dir)
    out_img = Path(output_dir) / "images" / split
    out_lbl = Path(output_dir) / "labels" / split
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    xml_files = list(xml_dir.glob("*.xml"))
    for xml_path in tqdm(xml_files, desc=f"Converting VOC [{split}]"):
        tree = ET.parse(str(xml_path))
        root = tree.getroot()

        fn_el = root.find("filename")
        if fn_el is None:
            continue

        img_path = image_dir / fn_el.text
        if not img_path.exists():
            for ext in [".jpg", ".png", ".JPG"]:
                img_path = image_dir / f"{xml_path.stem}{ext}"
                if img_path.exists():
                    break
            else:
                continue

        img = cv2.imread(str(img_path))
        if img is None:
            continue
        h, w = img.shape[:2]

        labels = []
        for obj in root.findall("object"):
            name = obj.find("name")
            bndbox = obj.find("bndbox")
            if name is None or bndbox is None:
                continue
            if name.text not in class_map:
                continue

            cls_id = class_map[name.text]
            x1 = float(bndbox.find("xmin").text)
            y1 = float(bndbox.find("ymin").text)
            x2 = float(bndbox.find("xmax").text)
            y2 = float(bndbox.find("ymax").text)

            cx = ((x1 + x2) / 2) / w
            cy = ((y1 + y2) / 2) / h
            bw = (x2 - x1) / w
            bh = (y2 - y1) / h
            labels.append(f"{cls_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

        if labels:
            shutil.copy2(str(img_path), str(out_img / img_path.name))
            (out_lbl / f"{img_path.stem}.txt").write_text("".join(labels))

    print(f"  {split}: 完成")


def convert_coco_dataset(
    coco_json: str,
    image_dir: str,
    output_dir: str,
    split: str = "train",
):
    """
    COCO JSON → YOLOv8-seg polygon 格式
    """
    with open(coco_json, "r") as f:
        coco = json.load(f)

    image_dir = Path(image_dir)
    out_img = Path(output_dir) / "images" / split
    out_lbl = Path(output_dir) / "labels" / split
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    # 构建索引
    cat_map = {cat["id"]: i for i, cat in enumerate(coco.get("categories", []))}
    img_map = {img["id"]: img for img in coco.get("images", [])}
    ann_map = {}
    for ann in coco.get("annotations", []):
        ann_map.setdefault(ann["image_id"], []).append(ann)

    for img_id, img_info in tqdm(img_map.items(), desc=f"Converting COCO [{split}]"):
        img_path = image_dir / img_info["file_name"]
        if not img_path.exists():
            continue

        h, w = img_info["height"], img_info["width"]
        lines = []

        for ann in ann_map.get(img_id, []):
            cls_id = cat_map.get(ann["category_id"], 0)

            if "segmentation" in ann and ann["segmentation"]:
                # polygon 分割
                for seg in ann["segmentation"]:
                    pts = []
                    for i in range(0, len(seg), 2):
                        pts.extend([seg[i] / w, seg[i + 1] / h])
                    lines.append(f"{cls_id} " + " ".join(f"{p:.6f}" for p in pts) + "\n")
            else:
                # bbox only
                x, y, bw_box, bh_box = ann["bbox"]
                cx = (x + bw_box / 2) / w
                cy = (y + bh_box / 2) / h
                nw = bw_box / w
                nh = bh_box / h
                lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}\n")

        if lines:
            shutil.copy2(str(img_path), str(out_img / img_info["file_name"]))
            (out_lbl / f"{img_path.stem}.txt").write_text("".join(lines))

    print(f"  {split}: 完成")


# ============================================================
# 数据集划分
# ============================================================

def split_dataset(
    image_dir: str,
    output_dir: str,
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    test_ratio: float = 0.1,
    seed: int = 42,
):
    """
    随机划分数据集 train/val/test

    对标论文: 7:2:1 划分, 3000 张历史数据训练
    """
    random.seed(seed)

    image_dir = Path(image_dir)
    image_files = []
    for ext in ["*.jpg", "*.png", "*.JPG"]:
        image_files.extend(image_dir.glob(ext))
    random.shuffle(image_files)

    total = len(image_files)
    n_train = int(total * train_ratio)
    n_val = int(total * val_ratio)

    splits = {
        "train": image_files[:n_train],
        "val": image_files[n_train:n_train + n_val],
        "test": image_files[n_train + n_val:],
    }

    out_base = Path(output_dir)
    for split_name, files in splits.items():
        out_img = out_base / "images" / split_name
        out_lbl = out_base / "labels" / split_name
        out_img.mkdir(parents=True, exist_ok=True)
        out_lbl.mkdir(parents=True, exist_ok=True)
        for img_path in files:
            shutil.copy2(str(img_path), str(out_img / img_path.name))
            for lbl_ext in [".txt"]:
                lbl_src = img_path.with_suffix(lbl_ext)
                if lbl_src.exists():
                    shutil.copy2(str(lbl_src), str(out_lbl / lbl_src.name))
        print(f"  {split_name}: {len(files)} 张")


# ============================================================
# 生成配置
# ============================================================

def generate_data_yaml(
    output_path: str,
    class_names: list,
    train_dir: str = "images/train",
    val_dir: str = "images/val",
):
    """
    生成 YOLO 数据配置文件

    用法:
      generate_data_yaml("datasets/tunnel_defects.yaml",
                         ["crack", "leakage", "spalling"])
    """
    yaml_path = Path(output_path)
    data = {
        "path": str(yaml_path.parent),
        "train": train_dir,
        "val": val_dir,
        "nc": len(class_names),
        "names": {i: name for i, name in enumerate(class_names)},
    }
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    print(f"[OK] 配置 → {yaml_path}")
    for i, name in enumerate(class_names):
        print(f"     class_{i}: {name}")
