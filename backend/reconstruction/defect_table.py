# ============================================================
#  文件: backend/data_pre_processing/defect_table_generator.py
#  所属: SuoXing-Tuan / 数据融合与缺陷投影模块
#  职责: 缺陷汇总表格生成器
#        - 收集所有已投影到世界坐标系的缺陷
#        - 支持按时间/位置排序
#        - 输出 CSV / JSON 格式的结构化表格
#        - 输出格式可直接对接外部报表系统
#
#  输出列（按 final_data.md 约定）:
#    编号 | 类型 | 世界坐标(X,Y,Z) | 检测时间 | 置信度 | 关联帧ID
# ============================================================

import csv
import json
import logging
import math
from io import StringIO
from typing import Optional

logger = logging.getLogger("data_pre_processing.table")


class DefectRecord:
    """
    单条缺陷记录的数据结构。

    字段说明:
      defect_id:     缺陷唯一编号（如 "DEF_001"）
      defect_type:   缺陷类型（如 "裂缝", "渗水", "脱落", "变形"）
      world_x/y/z:   世界坐标系下的缺陷位置（米）
      timestamp_ns:  检测时的纳秒时间戳
      confidence:    检测置信度 [0.0, 1.0]
      frame_id:      关联的 SensorFrame 帧 ID
      extra:         扩展字段（如备注、严重等级等）
    """

    __slots__ = ("defect_id", "defect_type", "world_x", "world_y", "world_z",
                 "timestamp_ns", "confidence", "frame_id", "extra")

    def __init__(self, defect_id: str, defect_type: str,
                 world_x: float, world_y: float, world_z: float,
                 timestamp_ns: int = 0, confidence: float = 0.0,
                 frame_id: str = "", extra: Optional[dict] = None):
        self.defect_id = defect_id
        self.defect_type = defect_type
        self.world_x = world_x
        self.world_y = world_y
        self.world_z = world_z
        self.timestamp_ns = timestamp_ns
        self.confidence = confidence
        self.frame_id = frame_id
        self.extra = extra or {}

    def to_dict(self) -> dict:
        """转为字典，用于 JSON 序列化。"""
        return {
            "defect_id": self.defect_id,
            "type": self.defect_type,
            "world_coord": {
                "x": self.world_x,
                "y": self.world_y,
                "z": self.world_z,
            },
            "timestamp_ns": self.timestamp_ns,
            "confidence": self.confidence,
            "frame_id": self.frame_id,
        }

    def to_csv_row(self) -> list:
        """转为 CSV 行（列表格式）。"""
        return [
            self.defect_id,
            self.defect_type,
            f"{self.world_x:.4f}",
            f"{self.world_y:.4f}",
            f"{self.world_z:.4f}",
            self.timestamp_ns,
            f"{self.confidence:.4f}",
            self.frame_id,
        ]

    @staticmethod
    def csv_header() -> list[str]:
        """CSV 表头。"""
        return ["编号", "类型", "世界坐标X(m)", "世界坐标Y(m)", "世界坐标Z(m)",
                "时间戳(ns)", "置信度", "关联帧ID"]


class DefectTableGenerator:
    """
    缺陷汇总表格生成器。

    收集缺陷记录 → 排序 → 导出 CSV / JSON。

    使用方式:
      table_gen = DefectTableGenerator()
      table_gen.add_defect(defect_dict)  # 逐条添加
      table_gen.add_defects_batch(defect_list)  # 批量添加
      csv_str = table_gen.to_csv()
      json_str = table_gen.to_json()
    """

    def __init__(self):
        """初始化表格生成器。"""
        self._defects: list[DefectRecord] = []

        # ── 可配置的默认排序方式 ──
        self._default_sort = "time"  # "time" | "position"

        logger.info("DefectTableGenerator 初始化完成")

    # ================================================================
    #  添加记录
    # ================================================================

    def add_defect(self, defect: dict) -> None:
        """
        添加单条缺陷记录。

        参数:
          defect: 缺陷字典（来自 DefectProjector 的输出），包含:
            - defect_id: 缺陷编号
            - type: 缺陷类型
            - world_coord: {"x","y","z"}
            - timestamp_ns: 检测时间戳
            - confidence: 置信度
            - frame_id: 关联帧ID
        """
        wc = defect.get("world_coord", {})
        record = DefectRecord(
            defect_id=defect.get("defect_id", "unknown"),
            defect_type=defect.get("type", "unknown"),
            world_x=wc.get("x", 0.0),
            world_y=wc.get("y", 0.0),
            world_z=wc.get("z", 0.0),
            timestamp_ns=defect.get("timestamp_ns", 0),
            confidence=defect.get("confidence", 0.0),
            frame_id=defect.get("frame_id", ""),
            extra=defect.get("extra"),
        )
        self._defects.append(record)

    def add_defects_batch(self, defect_list: list[dict]) -> None:
        """
        批量添加缺陷记录。

        参数:
          defect_list: 缺陷字典列表
        """
        for d in defect_list:
            self.add_defect(d)
        logger.info("批量添加 %d 条缺陷记录", len(defect_list))

    # ================================================================
    #  排序
    # ================================================================

    def sort_by_time(self, ascending: bool = True) -> None:
        """
        按检测时间排序。

        参数:
          ascending: True = 最早在前，False = 最新在前
        """
        self._defects.sort(key=lambda d: d.timestamp_ns, reverse=not ascending)
        logger.debug("按时间排序完成 (%s)", "升序" if ascending else "降序")

    def sort_by_position(self, axis: str = "x", ascending: bool = True) -> None:
        """
        按世界坐标位置排序。

        参数:
          axis: 排序轴 ("x", "y", "z")
          ascending: True = 升序
        """
        if axis == "x":
            key = lambda d: d.world_x
        elif axis == "y":
            key = lambda d: d.world_y
        elif axis == "z":
            key = lambda d: d.world_z
        else:
            logger.warning("未知排序轴 '%s'，使用 x 轴", axis)
            key = lambda d: d.world_x

        self._defects.sort(key=key, reverse=not ascending)
        logger.debug("按位置(%s轴)排序完成 (%s)", axis, "升序" if ascending else "降序")

    def sort_by_distance_from(self, ref_x: float, ref_y: float,
                              ref_z: float = 0.0) -> None:
        """
        按距离参考点的欧氏距离排序（最近的在前）。

        适用于"从某个位置出发，找出最近的缺陷"等查询场景。

        参数:
          ref_x, ref_y, ref_z: 参考点世界坐标
        """
        def distance(d: DefectRecord) -> float:
            return math.sqrt(
                (d.world_x - ref_x) ** 2 +
                (d.world_y - ref_y) ** 2 +
                (d.world_z - ref_z) ** 2
            )
        self._defects.sort(key=distance)
        logger.debug("按距离 (%.2f, %.2f, %.2f) 排序完成", ref_x, ref_y, ref_z)

    # ================================================================
    #  导出
    # ================================================================

    def to_csv(self, filepath: Optional[str] = None,
               sort: str = "time") -> str:
        """
        导出为 CSV 格式。

        参数:
          filepath: 若提供，写入文件；否则返回字符串
          sort: 导出前排序方式 ("time" | "position" | "none")

        返回:
          CSV 字符串
        """
        # ── 排序 ──
        if sort == "time" and self._defects:
            self.sort_by_time()
        elif sort == "position" and self._defects:
            self.sort_by_position()

        # ── 写入 ──
        output = StringIO()
        writer = csv.writer(output, lineterminator='\n')
        writer.writerow(DefectRecord.csv_header())
        for d in self._defects:
            writer.writerow(d.to_csv_row())

        csv_str = output.getvalue()
        output.close()

        # ── 保存到文件 ──
        if filepath:
            with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
                f.write(csv_str)
            logger.info("CSV 已保存到: %s (%d 条记录)", filepath, len(self._defects))

        return csv_str

    def to_json(self, filepath: Optional[str] = None,
                sort: str = "time", pretty: bool = True) -> str:
        """
        导出为 JSON 格式。

        参数:
          filepath: 若提供，写入文件；否则返回字符串
          sort: 导出前排序方式 ("time" | "position" | "none")
          pretty: 是否格式化（缩进）

        返回:
          JSON 字符串
        """
        # ── 排序 ──
        if sort == "time" and self._defects:
            self.sort_by_time()
        elif sort == "position" and self._defects:
            self.sort_by_position()

        # ── 构建输出结构 ──
        data = {
            "total": len(self._defects),
            "generated_at_ns": 0,  # 外部可覆盖
            "defects": [d.to_dict() for d in self._defects],
        }

        indent = 2 if pretty else None
        json_str = json.dumps(data, ensure_ascii=False, indent=indent)

        # ── 保存到文件 ──
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json_str)
            logger.info("JSON 已保存到: %s (%d 条记录)", filepath, len(self._defects))

        return json_str

    def to_summary_dict(self) -> dict:
        """
        生成缺陷汇总统计。

        返回按类型统计的数量、平均置信度等信息。
        """
        if not self._defects:
            return {"total": 0, "by_type": {}}

        by_type: dict[str, dict] = {}
        for d in self._defects:
            if d.defect_type not in by_type:
                by_type[d.defect_type] = {
                    "count": 0,
                    "confidence_sum": 0.0,
                    "confidence_max": 0.0,
                    "confidence_min": 1.0,
                }
            stats = by_type[d.defect_type]
            stats["count"] += 1
            stats["confidence_sum"] += d.confidence
            stats["confidence_max"] = max(stats["confidence_max"], d.confidence)
            stats["confidence_min"] = min(stats["confidence_min"], d.confidence)

        # 计算平均值
        summary_by_type = {}
        for t, s in by_type.items():
            summary_by_type[t] = {
                "count": s["count"],
                "avg_confidence": round(s["confidence_sum"] / s["count"], 4),
                "max_confidence": round(s["confidence_max"], 4),
                "min_confidence": round(s["confidence_min"], 4),
            }

        return {
            "total": len(self._defects),
            "by_type": summary_by_type,
        }

    # ================================================================
    #  查询
    # ================================================================

    @property
    def count(self) -> int:
        """当前缺陷总数。"""
        return len(self._defects)

    @property
    def all_defects(self) -> list[DefectRecord]:
        """返回所有缺陷记录的只读列表。"""
        return list(self._defects)

    def filter_by_type(self, defect_type: str) -> list[DefectRecord]:
        """按类型筛选缺陷。"""
        return [d for d in self._defects if d.defect_type == defect_type]

    def filter_by_frame(self, frame_id: str) -> list[DefectRecord]:
        """按关联帧ID筛选缺陷。"""
        return [d for d in self._defects if d.frame_id == frame_id]

    def filter_by_confidence(self, min_confidence: float) -> list[DefectRecord]:
        """按最小置信度筛选。"""
        return [d for d in self._defects if d.confidence >= min_confidence]

    def clear(self) -> None:
        """清空所有记录。"""
        self._defects.clear()
        logger.info("缺陷记录已清空")
