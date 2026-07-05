# ============================================================
# model-training/yolo-training/dataset.py
# 数据格式转换工具
# 把各种来源的数据集统一转成 YOLO 格式
#
# YOLO 格式说明:
#   每张图对应一个同名 .txt, 每行一个目标:
#     class_id x_center y_center width height
#   所有坐标归一化到 0~1 (除以图片宽高)
#
# 数据集目录结构 (训练前必须整理成这样):
#   datasets/
#   ├── images/
#   │   ├── train/
#   │   │   ├── img_001.jpg
#   │   │   └── ...
#   │   └── val/
#   │       └── ...
#   ├── labels/
#   │   ├── train/
#   │   │   ├── img_001.txt
#   │   │   └── ...
#   │   └── val/
#   │       └── ...
#   └── tunnel_defects.yaml   ← 数据配置 (自动生成)
# ============================================================

import cv2
import numpy as np
from pathlib import Path
from typing import Optional
import shutil
import yaml
from tqdm import tqdm


def mask_to_bbox(mask_path: str) -> Optional[list]:
    """
    把分割 mask (png, 0=背景, >0=缺陷区域) 转为 bbox
    返回: [x_center, y_center, width, height] 归一化
    """
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None or mask.max() == 0:
        return None

    # 找到所有非零像素的轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    bboxes = []
    h, w = mask.shape
    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw < 3 or bh < 3:  # 过滤太小的噪声
            continue
        # 转为 YOLO 格式 (center_x, center_y, width, height) 归一化
        cx = (x + bw / 2) / w
        cy = (y + bh / 2) / h
        nw = bw / w
        nh = bh / h
        bboxes.append([cx, cy, nw, nh])
    return bboxes


def convert_mask_dataset(
    image_dir: str,
    mask_dir: str,
    output_dir: str,
    class_id: int = 0,
    split: str = "train",
):
    """
    把 mask 分割标注的数据集转为 YOLO bbox 格式

    参数:
      image_dir:  图片目录
      mask_dir:   mask 目录 (同名 png, 缺陷区域>0)
      output_dir: 输出根目录 (会创建 images/{split}/ 和 labels/{split}/)
      class_id:   所有缺陷给同一个类别编号
      split:      "train" 或 "val"
    """
    image_dir = Path(image_dir)
    mask_dir = Path(mask_dir)
    out_img = Path(output_dir) / "images" / split
    out_lbl = Path(output_dir) / "labels" / split
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    image_files = list(image_dir.glob("*.jpg")) + list(image_dir.glob("*.png"))
    print(f"Converting {len(image_files)} images from mask to YOLO bbox format...")

    for img_path in tqdm(image_files):
        # 找对应的 mask
        mask_path = mask_dir / f"{img_path.stem}.png"
        if not mask_path.exists():
            mask_path = mask_dir / f"{img_path.stem}_mask.png"
        if not mask_path.exists():
            continue

        bboxes = mask_to_bbox(str(mask_path))
        if bboxes is None:
            bboxes = []

        # 复制图片
        shutil.copy2(str(img_path), str(out_img / img_path.name))

        # 写 YOLO 标注
        label_path = out_lbl / f"{img_path.stem}.txt"
        with open(label_path, "w") as f:
            for bbox in bboxes:
                f.write(f"{class_id} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}\n")


def convert_voc_to_yolo(
    xml_dir: str,
    image_dir: str,
    output_dir: str,
    class_map: dict,
    split: str = "train",
):
    """
    把 VOC 格式 (xml 标注) 转为 YOLO 格式

    参数:
      xml_dir:    Annotations/ 目录
      image_dir:  JPEGImages/ 目录
      output_dir: 输出根目录
      class_map:  {"类名": class_id, ...}
      split:      "train" 或 "val"
    """
    import xml.etree.ElementTree as ET

    xml_dir = Path(xml_dir)
    image_dir = Path(image_dir)
    out_img = Path(output_dir) / "images" / split
    out_lbl = Path(output_dir) / "labels" / split
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    xml_files = list(xml_dir.glob("*.xml"))
    print(f"Converting {len(xml_files)} XML annotations to YOLO format...")

    for xml_path in tqdm(xml_files):
        tree = ET.parse(str(xml_path))
        root = tree.getroot()

        # 找对应图片
        filename = root.find("filename").text
        img_path = image_dir / filename
        if not img_path.exists():
            # 尝试常见扩展名
            for ext in [".jpg", ".png", ".JPG", ".PNG"]:
                img_path = image_dir / f"{xml_path.stem}{ext}"
                if img_path.exists():
                    break
            else:
                continue

        # 读图片尺寸
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        h, w = img.shape[:2]

        # 转 bbox
        labels = []
        for obj in root.findall("object"):
            cls_name = obj.find("name").text
            if cls_name not in class_map:
                continue
            cls_id = class_map[cls_name]
            bndbox = obj.find("bndbox")
            x1 = float(bndbox.find("xmin").text)
            y1 = float(bndbox.find("ymin").text)
            x2 = float(bndbox.find("xmax").text)
            y2 = float(bndbox.find("ymax").text)
            # 转 YOLO 格式
            cx = ((x1 + x2) / 2) / w
            cy = ((y1 + y2) / 2) / h
            bw = (x2 - x1) / w
            bh = (y2 - y1) / h
            labels.append(f"{cls_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

        # 复制图片
        shutil.copy2(str(img_path), str(out_img / img_path.name))

        # 写标注
        lbl_path = out_lbl / f"{img_path.stem}.txt"
        with open(lbl_path, "w") as f:
            f.writelines(labels)


def generate_data_yaml(
    output_path: str,
    class_names: list,
    train_img_dir: str = "images/train",
    val_img_dir: str = "images/val",
):
    """
    生成 YOLO 数据配置文件 tunnel_defects.yaml

    参数:
      output_path:   保存路径, 如 "datasets/tunnel_defects.yaml"
      class_names:   类别名列表
      train_img_dir: 训练图片目录 (相对于 yaml 所在目录)
      val_img_dir:   验证图片目录
    """
    yaml_path = Path(output_path)
    data = {
        "path": str(yaml_path.parent.absolute()),
        "train": train_img_dir,
        "val": val_img_dir,
        "nc": len(class_names),
        "names": {i: name for i, name in enumerate(class_names)},
    }
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    print(f"Data config saved to: {yaml_path}")
    print(f"Classes ({len(class_names)}): {class_names}")


# ============================================================
# 快速使用示例 (在 Python 中运行):
#
#   from dataset import convert_mask_dataset, generate_data_yaml, CLASS_NAMES
#
#   # 1. 把 cuijingqi 的 mask 数据集转成 YOLO bbox 格式
#   convert_mask_dataset(
#       image_dir="datasets/tunnel/crack/",
#       mask_dir="datasets/tunnel/crack_mask/",
#       output_dir="datasets/tunnel/",
#       class_id=0,   # 0 = crack
#       split="train"
#   )
#
#   # 2. 生成 yaml 配置
#   generate_data_yaml(
#       output_path="datasets/tunnel_defects.yaml",
#       class_names=CLASS_NAMES,
#   )
# ============================================================
