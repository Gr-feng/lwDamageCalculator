from __future__ import annotations

import csv
import json
import os
import traceback
from collections import OrderedDict
from dataclasses import asdict
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from combat_constants import BULLET_RAW_LABELS, ELEMENT_RAW_LABELS
from gui.config import AllySlotConfig, AppConfig, EnemySlotConfig, ProcessConfig
from gui.resources import CHARACTER_CSV_PATH, DATA_DIR, ICON_PATH, NOTICE_JSON_PATH, PRESET_DIR
from gui.services import CharacterIndex, DamageCalculatorService
from gui.widgets import (
    AllySlotWidget,
    CharacterDetailWidget,
    CharacterQueryWidget,
    CollapsibleSection,
    EnemySlotWidget,
    EquipmentQueryWidget,
    FieldBuffWidget,
)


class MainWindow(QMainWindow):
    DETAIL_HEADERS = ["段落", "段落名", "属性", "弹种", "阴阳", "伤害", "我方基础攻击", "敌方基础防御", "特攻", "弱点"]
    SEGMENT_LABELS = {
        0: "第一段",
        1: "第二段",
        2: "第三段",
        3: "第四段",
        4: "第五段",
        5: "第六段",
    }
    SCROLLBAR_STYLE = """
        QScrollBar:vertical {
            background: #edf1f6;
            width: 22px;
            margin: 0;
            border-radius: 10px;
        }
        QScrollBar::handle:vertical {
            background: #8fa4bf;
            min-height: 64px;
            border-radius: 10px;
            border: 3px solid #edf1f6;
        }
        QScrollBar::handle:vertical:hover {
            background: #6f88a7;
        }
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0;
        }
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {
            background: transparent;
        }
        QScrollBar:horizontal {
            background: #edf1f6;
            height: 18px;
            margin: 0;
            border-radius: 9px;
        }
        QScrollBar::handle:horizontal {
            background: #8fa4bf;
            min-width: 48px;
            border-radius: 9px;
            border: 2px solid #edf1f6;
        }
        QScrollBar::handle:horizontal:hover {
            background: #6f88a7;
        }
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {
            width: 0;
        }
        QScrollBar::add-page:horizontal,
        QScrollBar::sub-page:horizontal {
            background: transparent;
        }
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("东方归言录伤害计算器 v1.1")
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self.resize(980, 720)
        self.service = DamageCalculatorService(DATA_DIR)
        self.char_index = CharacterIndex(CHARACTER_CSV_PATH)
        os.makedirs(PRESET_DIR, exist_ok=True)
        self.last_result: Optional[Dict[str, Any]] = None
        self._build_ui()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        QTimer.singleShot(0, self._show_startup_notice_if_needed)

    def _load_startup_notice(self) -> Optional[Dict[str, Any]]:
        if not os.path.exists(NOTICE_JSON_PATH):
            return None
        try:
            with open(NOTICE_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or not data.get("enabled", True):
                return None
            return data
        except Exception:
            return None

    def _show_startup_notice_if_needed(self):
        data = self._load_startup_notice()
        if not data:
            return
        text = str(data.get("text", "")).strip()
        if not text:
            return
        box = QMessageBox(self)
        box.setWindowTitle(str(data.get("title", "提示")))
        icon_map = {
            "information": QMessageBox.Information,
            "warning": QMessageBox.Warning,
            "critical": QMessageBox.Critical,
            "question": QMessageBox.Question,
        }
        box.setIcon(icon_map.get(str(data.get("icon", "information")).lower(), QMessageBox.Information))
        box.setText(text)
        box.exec()

    def _make_scroll_area(self, content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(self.SCROLLBAR_STYLE)
        scroll.verticalScrollBar().setSingleStep(48)
        scroll.horizontalScrollBar().setSingleStep(48)
        scroll.setWidget(content)
        return scroll

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)

        topbar = QHBoxLayout()
        self.preset_name_edit = QLineEdit()
        self.preset_name_edit.setPlaceholderText("preset 名称")
        save_btn = QPushButton("保存配置")
        load_btn = QPushButton("读取配置")
        save_btn.clicked.connect(self.on_save_preset)
        load_btn.clicked.connect(self.on_load_preset)
        topbar.addWidget(QLabel("Preset"))
        topbar.addWidget(self.preset_name_edit)
        topbar.addWidget(save_btn)
        topbar.addWidget(load_btn)
        root_layout.addLayout(topbar)

        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs)
        self.enemy_page = QWidget()
        self.ally_page = QWidget()
        self.process_page = QWidget()
        self.result_page = QWidget()
        self.tabs.addTab(self.enemy_page, "敌方参数")
        self.tabs.addTab(self.ally_page, "我方参数")
        self.tabs.addTab(self.process_page, "计算过程")
        self.tabs.addTab(self.result_page, "最终结果")
        self.character_query_page = QWidget()
        self.equipment_query_page = QWidget()
        self.character_detail_page = QWidget()
        self.tabs.addTab(self.character_query_page, "角色查询")
        self.tabs.addTab(self.equipment_query_page, "绘卷查询")
        self.tabs.addTab(self.character_detail_page, "角色详情")

        self._build_enemy_page()
        self._build_ally_page()
        self._build_process_page()
        self._build_result_page()
        self._build_character_query_page()
        self._build_equipment_query_page()
        self._build_character_detail_page()

    def _build_enemy_page(self):
        layout = QVBoxLayout(self.enemy_page)
        tabs = QTabWidget()
        self.enemy_widgets: Dict[int, EnemySlotWidget] = {}
        for pos in [0, 1, 2]:
            widget = EnemySlotWidget(pos, self.service, self.char_index)
            self.enemy_widgets[pos] = widget
            tabs.addTab(self._make_scroll_area(widget), f"位置{pos}")
        layout.addWidget(tabs)

    def _build_ally_page(self):
        layout = QVBoxLayout(self.ally_page)
        tabs = QTabWidget()
        self.ally_widgets: Dict[int, AllySlotWidget] = {}
        for pos in [0, 1, 2]:
            widget = AllySlotWidget(pos, self.service, self.char_index)
            self.ally_widgets[pos] = widget
            tabs.addTab(self._make_scroll_area(widget), f"位置{pos}")
        layout.addWidget(tabs)

    def _build_process_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        btns = QHBoxLayout()
        calc_btn = QPushButton("计算")
        calc_btn.clicked.connect(self.on_calculate)
        batch_btn = QPushButton("批量计算并导出 summary")
        batch_btn.clicked.connect(self.on_batch_export_summary)
        btns.addWidget(calc_btn)
        btns.addWidget(batch_btn)
        btns.addStretch(1)
        layout.addLayout(btns)

        order_box = QGroupBox("技能释放设置")
        order_layout = QVBoxLayout(order_box)
        self.custom_skill_order_check = QCheckBox("多角色时启用自定义全局技能释放顺序")
        self.custom_skill_order_check.toggled.connect(self._sync_custom_skill_order_state)
        self.custom_skill_order_edit = QLineEdit()
        self.custom_skill_order_edit.setPlaceholderText("示例: 0:0,1:0,0:1,2:0")
        hint = QLabel("格式为 角色位置:技能位。未勾选时仍按各角色自己的技能顺序文本执行。")
        hint.setWordWrap(True)
        order_layout.addWidget(self.custom_skill_order_check)
        order_layout.addWidget(self.custom_skill_order_edit)
        order_layout.addWidget(hint)
        layout.addWidget(order_box)
        self._sync_custom_skill_order_state()

        summary_box = QGroupBox("当前启用状态")
        summary_layout = QVBoxLayout(summary_box)
        self.enemy_state_label = QLabel("敌方: -")
        self.enemy_state_label.setWordWrap(True)
        self.ally_state_label = QLabel("我方: -")
        self.ally_state_label.setWordWrap(True)
        summary_layout.addWidget(self.enemy_state_label)
        summary_layout.addWidget(self.ally_state_label)
        layout.addWidget(summary_box)

        self.field_buff_widget = FieldBuffWidget()
        layout.addWidget(self.field_buff_widget)
        layout.addStretch(1)

        wrapper_layout = QVBoxLayout(self.process_page)
        wrapper_layout.addWidget(self._make_scroll_area(page))

    def _build_result_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        grid = QGridLayout()
        self.seg_labels: Dict[str, QLabel] = {}
        for i in range(6):
            key = f"seg{i}"
            grid.addWidget(QLabel(self.SEGMENT_LABELS[i]), i // 3, (i % 3) * 2)
            lbl = QLabel("0")
            self.seg_labels[key] = lbl
            grid.addWidget(lbl, i // 3, (i % 3) * 2 + 1)
        grid.addWidget(QLabel("敌方0"), 2, 0)
        self.enemy0_label = QLabel("0")
        grid.addWidget(self.enemy0_label, 2, 1)
        grid.addWidget(QLabel("敌方1"), 2, 2)
        self.enemy1_label = QLabel("0")
        grid.addWidget(self.enemy1_label, 2, 3)
        grid.addWidget(QLabel("敌方2"), 2, 4)
        self.enemy2_label = QLabel("0")
        grid.addWidget(self.enemy2_label, 2, 5)
        grid.addWidget(QLabel("overall"), 3, 0)
        self.total_label = QLabel("0")
        grid.addWidget(self.total_label, 3, 1)
        grid.addWidget(QLabel("阴阳判定"), 3, 2)
        self.yinyang_role_label = QLabel("阴阳均衡")
        grid.addWidget(self.yinyang_role_label, 3, 3)
        grid.addWidget(QLabel("yang_ratio"), 3, 4)
        self.yang_ratio_label = QLabel("0.000")
        grid.addWidget(self.yang_ratio_label, 3, 5)
        layout.addLayout(grid)

        self.ally_damage_tabs = QTabWidget()
        self.ally_damage_labels: Dict[int, Dict[str, QLabel]] = {}
        for pos in [0, 1, 2]:
            tab_page = QWidget()
            pg = QGridLayout(tab_page)
            labels: Dict[str, QLabel] = {}
            for i in range(6):
                key = f"seg{i}"
                pg.addWidget(QLabel(self.SEGMENT_LABELS[i]), i // 3, (i % 3) * 2)
                lbl = QLabel("0")
                labels[key] = lbl
                pg.addWidget(lbl, i // 3, (i % 3) * 2 + 1)
            pg.addWidget(QLabel("total"), 2, 0)
            total_lbl = QLabel("0")
            labels["total"] = total_lbl
            pg.addWidget(total_lbl, 2, 1)
            self.ally_damage_labels[pos] = labels
            self.ally_damage_tabs.addTab(tab_page, f"我方 {pos} 伤害")
        layout.addWidget(self.ally_damage_tabs)

        self.result_debug_text = QPlainTextEdit()
        self.result_debug_text.setReadOnly(True)
        self.result_debug_text.setMaximumHeight(180)
        layout.addWidget(CollapsibleSection("结果 JSON", self.result_debug_text, expanded=False))

        self.detail_tabs = QTabWidget()
        self.detail_tables: Dict[str, QTableWidget] = {}
        for key, label in (("all", "总计"), ("enemy0", "敌方0"), ("enemy1", "敌方1"), ("enemy2", "敌方2")):
            table = self._create_result_detail_table()
            self.detail_tables[key] = table
            self.detail_tabs.addTab(table, label)
        layout.addWidget(self.detail_tabs)
        layout.addStretch(1)

        wrapper_layout = QVBoxLayout(self.result_page)
        wrapper_layout.addWidget(self._make_scroll_area(page))

    def _build_character_query_page(self):
        layout = QVBoxLayout(self.character_query_page)
        self.character_query_widget = CharacterQueryWidget(self.service, self.open_character_detail)
        layout.addWidget(self._make_scroll_area(self.character_query_widget))

    def _build_equipment_query_page(self):
        layout = QVBoxLayout(self.equipment_query_page)
        self.equipment_query_widget = EquipmentQueryWidget(self.service)
        layout.addWidget(self._make_scroll_area(self.equipment_query_widget))

    def _build_character_detail_page(self):
        layout = QVBoxLayout(self.character_detail_page)
        self.character_detail_widget = CharacterDetailWidget(self.service)
        layout.addWidget(self._make_scroll_area(self.character_detail_widget))

    def _on_tab_changed(self, index: int):
        self.refresh_process_state_summary()
        if getattr(self, "character_detail_widget", None) is None:
            return
        if self.tabs.widget(index) is not self.character_detail_page:
            self.character_detail_widget.deactivate()

    def open_character_detail(self, char_id: int):
        self.character_detail_widget.load_character(int(char_id))
        self.tabs.setCurrentWidget(self.character_detail_page)

    def _sync_custom_skill_order_state(self):
        self.custom_skill_order_edit.setEnabled(self.custom_skill_order_check.isChecked())

    @staticmethod
    def _format_display_value(value: Any) -> str:
        try:
            num = float(value)
        except Exception:
            return str(value)
        if abs(num - round(num)) <= 1e-9:
            return str(int(round(num)))
        return f"{num:.2f}".rstrip("0").rstrip(".")

    def _create_result_detail_table(self) -> QTableWidget:
        table = QTableWidget(0, len(self.DETAIL_HEADERS))
        table.setHorizontalHeaderLabels(self.DETAIL_HEADERS)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)
        return table

    def _set_result_detail_rows(self, table: QTableWidget, details: list[Dict[str, Any]]):
        table.setRowCount(len(details))
        for r, d in enumerate(details):
            hit = d.get("hit", {}) or {}
            ei = d.get("element_info", {}) or {}
            weak = (ei.get("quality_value") == 0) or (ei.get("element_mode") == "advantage")
            is_killer = str(hit.get("crit_mode", "")).lower() == "killer"
            element_label = ELEMENT_RAW_LABELS.get(int(d.get("element", 0) or 0), d.get("element", ""))
            bullet_label = BULLET_RAW_LABELS.get(int(d.get("bullet_type", 0) or 0), d.get("bullet_type", ""))
            try:
                seg_label = self.SEGMENT_LABELS.get(int(d.get("seg", -1)), str(d.get("seg", "")))
            except Exception:
                seg_label = str(d.get("seg", ""))
            yinyang_value = d.get("yinyang", "")
            yinyang_label = "阳" if str(yinyang_value) == "1" else ("阴" if str(yinyang_value) == "0" else str(yinyang_value))
            row = [
                seg_label,
                d.get("shot_name", ""),
                element_label,
                bullet_label,
                yinyang_label,
                self._format_display_value(d.get("damage_int", "")),
                self._format_display_value(d.get("base_atk", "")),
                self._format_display_value(d.get("base_def", "")),
                "是" if is_killer else "否",
                "是" if weak else "否",
            ]
            for c, v in enumerate(row):
                item = QTableWidgetItem(str(v))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                table.setItem(r, c, item)
        table.resizeRowsToContents()

    def refresh_process_state_summary(self):
        enemy_parts = [f"[{pos}] {self._describe_widget(widget)}" for pos, widget in self.enemy_widgets.items() if widget.enabled_check.isChecked()]
        ally_parts = [f"[{pos}] {self._describe_widget(widget)}" for pos, widget in self.ally_widgets.items() if widget.enabled_check.isChecked()]
        self.enemy_state_label.setText("敌方: " + (" / ".join(enemy_parts) if enemy_parts else "-"))
        self.ally_state_label.setText("我方: " + (" / ".join(ally_parts) if ally_parts else "-"))

    @staticmethod
    def _describe_widget(widget) -> str:
        label_text = widget.name_world_label.text().strip()
        name = label_text.split("/", 1)[0].strip() if "/" in label_text else label_text
        return name if name and name != "-" else f"ID={widget.id_edit.text().strip()}"

    def gather_config(self) -> AppConfig:
        return AppConfig(
            enemy_slots={pos: w.get_config() for pos, w in self.enemy_widgets.items()},
            ally_slots={pos: w.get_config() for pos, w in self.ally_widgets.items()},
            process=ProcessConfig(
                use_custom_skill_order=self.custom_skill_order_check.isChecked(),
                custom_skill_order_text=self.custom_skill_order_edit.text().strip(),
                field_buffs=self.field_buff_widget.get_config(),
            ),
        )

    def apply_config(self, cfg: AppConfig):
        for pos in [0, 1, 2]:
            self.enemy_widgets[pos].apply_config(cfg.enemy_slots[pos])
            self.ally_widgets[pos].apply_config(cfg.ally_slots[pos])
        self.custom_skill_order_check.setChecked(cfg.process.use_custom_skill_order)
        self.custom_skill_order_edit.setText(cfg.process.custom_skill_order_text)
        self.field_buff_widget.set_config(cfg.process.field_buffs)
        self._sync_custom_skill_order_state()
        self.refresh_process_state_summary()

    def on_save_preset(self):
        name = self.preset_name_edit.text().strip()
        if not name:
            QMessageBox.information(self, "提示", "请输入 preset 名称")
            return
        path = os.path.join(PRESET_DIR, f"{name}.json")
        cfg = self.gather_config()
        payload = {
            "enemy_slots": {str(k): asdict(v) for k, v in cfg.enemy_slots.items()},
            "ally_slots": {str(k): asdict(v) for k, v in cfg.ally_slots.items()},
            "process": asdict(cfg.process),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "保存完成", path)

    def on_load_preset(self):
        path, _ = QFileDialog.getOpenFileName(self, "读取配置", PRESET_DIR, "JSON Files (*.json)")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        enemy_slots = {pos: EnemySlotConfig(**payload.get("enemy_slots", {}).get(str(pos), {})) for pos in [0, 1, 2]}
        ally_slots = {pos: AllySlotConfig(**payload.get("ally_slots", {}).get(str(pos), {})) for pos in [0, 1, 2]}
        process = ProcessConfig.from_payload(payload.get("process"))
        self.apply_config(AppConfig(enemy_slots=enemy_slots, ally_slots=ally_slots, process=process))
        QMessageBox.information(self, "读取完成", path)

    def on_calculate(self):
        self.refresh_process_state_summary()
        try:
            cfg = self.gather_config()
            result = self.service.run_single(cfg.enemy_slots, cfg.ally_slots, process_config=cfg.process)
            self.last_result = result
            self.render_result(result)
            self.tabs.setCurrentWidget(self.result_page)
        except Exception:
            QMessageBox.critical(self, "计算失败", traceback.format_exc())

    def render_result(self, result: Dict[str, Any]):
        seg_damage = result.get("seg_damage", {}) or {}
        for i in range(6):
            self.seg_labels[f"seg{i}"].setText(self._format_display_value(seg_damage.get(f"seg{i}", 0)))
        enemy_totals = result.get("enemy_totals", {}) or {}
        self.enemy0_label.setText(self._format_display_value(enemy_totals.get(0, 0)))
        self.enemy1_label.setText(self._format_display_value(enemy_totals.get(1, 0)))
        self.enemy2_label.setText(self._format_display_value(enemy_totals.get(2, 0)))
        self.total_label.setText(self._format_display_value(result.get("total_damage", 0)))
        self.yinyang_role_label.setText(str(result.get("yinyang_role", "阴阳均衡")))
        self.yang_ratio_label.setText(self._format_display_value(result.get("yang_ratio", 0.0)))

        ally_totals = result.get("ally_totals", {}) or {}
        ally_seg = result.get("ally_seg_damage", {}) or {}
        for pos in [0, 1, 2]:
            labels = self.ally_damage_labels[pos]
            segs = ally_seg.get(pos, {}) if isinstance(ally_seg, dict) else {}
            for i in range(6):
                labels[f"seg{i}"].setText(self._format_display_value(segs.get(f"seg{i}", 0)))
            labels["total"].setText(self._format_display_value(ally_totals.get(pos, 0)))

        payload = {
            "skill_order": result.get("skill_order", []),
            "field_buffs": result.get("field_buffs", {}),
            "total_damage": result.get("total_damage", 0),
            "yang_damage_total": result.get("yang_damage_total", 0),
            "yin_damage_total": result.get("yin_damage_total", 0),
            "yang_ratio": result.get("yang_ratio", 0.0),
            "yin_ratio": result.get("yin_ratio", 0.0),
            "yinyang_role": result.get("yinyang_role", "阴阳均衡"),
        }
        self.result_debug_text.setPlainText(json.dumps(payload, ensure_ascii=False, indent=2, default=str))

        details = result.get("details", []) or []
        self._set_result_detail_rows(self.detail_tables["all"], details)
        for enemy_pos in (0, 1, 2):
            filtered = []
            for d in details:
                raw_enemy_pos = d.get("enemy_pos", -1)
                try:
                    current_enemy_pos = int(raw_enemy_pos if raw_enemy_pos is not None else -1)
                except Exception:
                    current_enemy_pos = -1
                if current_enemy_pos == enemy_pos:
                    filtered.append(d)
            self._set_result_detail_rows(self.detail_tables[f"enemy{enemy_pos}"], filtered)

    def _calc_enemy_seg_flag_counts(self, result: Dict[str, Any]) -> Dict[str, Any]:
        details = result.get("details", []) or []
        valid_segs = set(range(6))
        weak_segs_by_enemy = {0: set(), 1: set(), 2: set()}
        killer_segs_by_enemy = {0: set(), 1: set(), 2: set()}
        for d in details:
            try:
                seg = int(d.get("seg", -1))
                enemy_pos = int(d.get("enemy_pos", -1))
            except Exception:
                continue
            if seg not in valid_segs or enemy_pos not in (0, 1, 2):
                continue
            hit = d.get("hit", {}) or {}
            ei = d.get("element_info", {}) or {}
            if (ei.get("quality_value") == 0) or (ei.get("element_mode") == "advantage"):
                weak_segs_by_enemy[enemy_pos].add(seg)
            if str(hit.get("crit_mode", "")).lower() == "killer":
                killer_segs_by_enemy[enemy_pos].add(seg)
        return {
            "enemy_pos_0_weak_seg_count": len(weak_segs_by_enemy[0]),
            "enemy_pos_0_killer_seg_count": len(killer_segs_by_enemy[0]),
            "enemy_pos_1_weak_seg_count": len(weak_segs_by_enemy[1]),
            "enemy_pos_1_killer_seg_count": len(killer_segs_by_enemy[1]),
            "enemy_pos_2_weak_seg_count": len(weak_segs_by_enemy[2]),
            "enemy_pos_2_killer_seg_count": len(killer_segs_by_enemy[2]),
        }

    def _build_summary_row(
        self,
        result: Dict[str, Any],
        cid: int,
        name: str,
        world_group: str,
        character_type: str,
        ally_cfg: AllySlotConfig,
    ) -> Dict[str, Any]:
        seg = result.get("seg_damage", {}) or {}
        enemy_totals = result.get("enemy_totals", {}) or {}
        seg_flag_stats = self._calc_enemy_seg_flag_counts(result)
        equipment = self.service.get_equipment_for_attack_type(ally_cfg.equipment_ids, ally_cfg.attack_type) or {}
        return {
            "character_id": cid,
            "character_name": name,
            "world_group": world_group,
            "character_type": character_type,
            "attack_type": ally_cfg.attack_type,
            "equipment_id": int(equipment.get("equipment_id", 0) or 0),
            "equipment_name": str(equipment.get("name", "") or ""),
            "skill_order": ally_cfg.skill_order_text,
            "spirit_level": ally_cfg.spirit_level,
            "target_enemy_pos": ally_cfg.target_enemy_pos,
            "seg0": seg.get("seg0", 0),
            "seg1": seg.get("seg1", 0),
            "seg2": seg.get("seg2", 0),
            "seg3": seg.get("seg3", 0),
            "seg4": seg.get("seg4", 0),
            "seg5": seg.get("seg5", 0),
            "enemy_pos_0_total": enemy_totals.get(0, 0),
            "enemy_pos_1_total": enemy_totals.get(1, 0),
            "enemy_pos_2_total": enemy_totals.get(2, 0),
            "enemy_pos_0_weak_seg_count": seg_flag_stats["enemy_pos_0_weak_seg_count"],
            "enemy_pos_0_killer_seg_count": seg_flag_stats["enemy_pos_0_killer_seg_count"],
            "enemy_pos_1_weak_seg_count": seg_flag_stats["enemy_pos_1_weak_seg_count"],
            "enemy_pos_1_killer_seg_count": seg_flag_stats["enemy_pos_1_killer_seg_count"],
            "enemy_pos_2_weak_seg_count": seg_flag_stats["enemy_pos_2_weak_seg_count"],
            "enemy_pos_2_killer_seg_count": seg_flag_stats["enemy_pos_2_killer_seg_count"],
            "overall_total": result.get("total_damage", 0),
            "yang_damage_total": result.get("yang_damage_total", 0),
            "yin_damage_total": result.get("yin_damage_total", 0),
            "yang_ratio": result.get("yang_ratio", 0.0),
            "yin_ratio": result.get("yin_ratio", 0.0),
            "yinyang_role": result.get("yinyang_role", "阴阳均衡"),
            "detail_count": len(result.get("details", []) or []),
        }

    @staticmethod
    def _translate_batch_summary_rows(rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        translated_rows: list[Dict[str, Any]] = []
        for row in rows:
            translated = OrderedDict()
            translated["角色ID"] = row.get("character_id", "")
            translated["角色原名"] = row.get("character_name", "")
            translated["角色名称"] = row.get("name_cn", "")
            translated["世界群"] = row.get("world_group", "")
            translated["类型"] = row.get("character_type", "")
            translated["攻击类型"] = row.get("attack_type", "")
            translated["绘卷ID"] = row.get("equipment_id", "")
            translated["绘卷名称"] = row.get("equipment_name", "")
            translated["技能顺序"] = row.get("skill_order", "")
            translated["开p数"] = row.get("spirit_level", "")
            translated["目标敌人"] = row.get("target_enemy_pos", "")
            translated["敌方0总伤害"] = row.get("enemy_pos_0_total", "")
            translated["敌方1总伤害"] = row.get("enemy_pos_1_total", "")
            translated["敌方2总伤害"] = row.get("enemy_pos_2_total", "")
            translated["总伤害"] = row.get("overall_total", "")
            translated["阳伤害"] = row.get("yang_damage_total", "")
            translated["阴伤害"] = row.get("yin_damage_total", "")
            translated["敌方0弱点段数"] = row.get("enemy_pos_0_weak_seg_count", "")
            translated["敌方0特攻段数"] = row.get("enemy_pos_0_killer_seg_count", "")
            translated["敌方1弱点段数"] = row.get("enemy_pos_1_weak_seg_count", "")
            translated["敌方1特攻段数"] = row.get("enemy_pos_1_killer_seg_count", "")
            translated["敌方2弱点段数"] = row.get("enemy_pos_2_weak_seg_count", "")
            translated["敌方2特攻段数"] = row.get("enemy_pos_2_killer_seg_count", "")
            translated["状态"] = row.get("status", "")
            translated["原因"] = row.get("reason", "")
            translated["第一段"] = row.get("seg0", "")
            translated["第二段"] = row.get("seg1", "")
            translated["第三段"] = row.get("seg2", "")
            translated["第四段"] = row.get("seg3", "")
            translated["第五段"] = row.get("seg4", "")
            translated["第六段"] = row.get("seg5", "")
            translated["阳占比"] = row.get("yang_ratio", "")
            translated["阴占比"] = row.get("yin_ratio", "")
            translated["阴阳定位"] = row.get("yinyang_role", "")
            translated_rows.append(translated)
        return translated_rows

    def on_export_summary(self):
        if not self.last_result:
            QMessageBox.information(self, "提示", "请先计算一次")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 summary.csv", "summary.csv", "CSV Files (*.csv)")
        if not path:
            return
        cfg0 = self.ally_widgets[0].get_config()
        cid = int(self.ally_widgets[0].id_edit.text().strip())
        name_world = self.ally_widgets[0].name_world_label.text().split(" / ")
        character_type = self.ally_widgets[0].type_label.text().strip()
        row = self._build_summary_row(
            self.last_result,
            cid,
            name_world[0] if name_world else "",
            name_world[1] if len(name_world) > 1 else "",
            character_type,
            cfg0,
        )
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            writer.writeheader()
            writer.writerow(row)
        QMessageBox.information(self, "导出完成", path)

    def on_batch_export_summary(self):
        self.refresh_process_state_summary()
        path, _ = QFileDialog.getSaveFileName(self, "批量导出 summary.csv", "batch_summary.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            cfg = self.gather_config()
            ally_template = self.ally_widgets[0].get_config()
            ally_template.enabled = True
            rows = self.service.run_batch_single_template(cfg.enemy_slots, ally_template, process_config=cfg.process)
            if not rows:
                raise RuntimeError("没有批量结果")
            output_rows = self._translate_batch_summary_rows(rows)
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(output_rows[0].keys()))
                writer.writeheader()
                writer.writerows(output_rows)
            QMessageBox.information(self, "批量导出完成", path)
        except Exception:
            QMessageBox.critical(self, "批量计算失败", traceback.format_exc())
