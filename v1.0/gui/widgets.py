from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QToolBox,
    QVBoxLayout,
    QWidget,
)

from combat_constants import (
    BULLET_RAW_LABELS,
    DEFAULT_ATTACK_TYPE,
    DEFAULT_SHIELD_OPEN_COUNT,
    DEFAULT_SPIRIT_LEVEL,
    ELEMENT_RAW_LABELS,
    QUALITY_DEFAULT,
    QUALITY_LABELS,
    QUALITY_STATE_TEXT,
    TYPE_LABELS,
)
from gui.config import AllySlotConfig, EnemySlotConfig, FieldBuffConfig
from gui.services import CharacterIndex, DamageCalculatorService


def _make_compact_field(
    label_text: str,
    widget: QWidget,
    *,
    label_width: int = 56,
    widget_width: Optional[int] = None,
    label_align: Qt.AlignmentFlag = Qt.AlignRight | Qt.AlignVCenter,
) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(3)
    layout.setAlignment(Qt.AlignLeft)
    label = QLabel(label_text)
    label.setAlignment(label_align)
    label.setMinimumWidth(label_width)
    label.setMaximumWidth(label_width + 8)
    if widget_width is not None:
        widget.setMaximumWidth(widget_width)
    layout.addWidget(label)
    layout.addWidget(widget, 0, Qt.AlignLeft)
    layout.addStretch(1)
    return container


def _make_inline_row(*widgets: QWidget, spacing: int = 8) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)
    layout.setAlignment(Qt.AlignLeft)
    for widget in widgets:
        layout.addWidget(widget, 0, Qt.AlignLeft)
    layout.addStretch(1)
    return container


class BuffTableWidget(QTableWidget):
    HEADERS = ["ID", "subID", "回合数", "值", "说明"]

    def __init__(self, service: DamageCalculatorService):
        super().__init__(0, 5)
        self.service = service
        self.setHorizontalHeaderLabels(self.HEADERS)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.setColumnWidth(0, 152)
        self.setColumnWidth(1, 172)
        self.setColumnWidth(2, 64)
        self.setColumnWidth(3, 64)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().setDefaultSectionSize(34)

    def _create_editable_combo(self, placeholder: str) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)
        combo.setSizeAdjustPolicy(QComboBox.AdjustToContentsOnFirstShow)
        combo.setMinimumWidth(136)
        if combo.lineEdit() is not None:
            combo.lineEdit().setPlaceholderText(placeholder)
        return combo

    def _create_line_edit(self, placeholder: str) -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMaximumWidth(72)
        return edit

    def _row_of_widget(self, widget: QWidget) -> int:
        for row in range(self.rowCount()):
            for col in range(4):
                if self.cellWidget(row, col) is widget:
                    return row
        return -1

    def _focused_row(self) -> int:
        widget = QApplication.focusWidget()
        while widget is not None:
            row = self._row_of_widget(widget)
            if row >= 0:
                return row
            widget = widget.parentWidget()
        return -1

    def _get_cell_text(self, row: int, col: int) -> str:
        widget = self.cellWidget(row, col)
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        item = self.item(row, col)
        return item.text().strip() if item else ""

    def _set_cell_text(self, row: int, col: int, text: Any):
        widget = self.cellWidget(row, col)
        raw = str(text if text is not None else "")
        if isinstance(widget, QComboBox):
            widget.setCurrentText(raw)
            return
        if isinstance(widget, QLineEdit):
            widget.setText(raw)
            return
        self.setItem(row, col, QTableWidgetItem(raw))

    def _populate_buff_id_combo(self, combo: QComboBox):
        current_text = combo.currentText().strip()
        combo.blockSignals(True)
        combo.clear()
        for buff_id, label in self.service.list_buff_id_options():
            combo.addItem(f"{buff_id} {label}", buff_id)
        combo.setCurrentText(current_text)
        combo.blockSignals(False)

    def _parse_leading_int(self, text: str) -> Optional[int]:
        token = str(text or "").strip().split(" ", 1)[0].strip()
        if not token:
            return None
        try:
            return int(float(token))
        except Exception:
            return None

    def _current_buff_id(self, row: int) -> int:
        return self._parse_leading_int(self._get_cell_text(row, 0)) or 0

    def _sync_subid_combo(self, row: int):
        combo = self.cellWidget(row, 1)
        if not isinstance(combo, QComboBox):
            return
        current_text = combo.currentText().strip()
        buff_id = self._current_buff_id(row)
        combo.blockSignals(True)
        combo.clear()
        for sub_id, label in self.service.list_buff_subid_options(buff_id):
            combo.addItem(f"{sub_id} {label}", sub_id)
        combo.setCurrentText(current_text)
        combo.blockSignals(False)

    def _set_desc_item(self, row: int, text: str):
        item = self.item(row, 4)
        if item is None:
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.setItem(row, 4, item)
        else:
            item.setText(text)

    def _refresh_row_description(self, row: int):
        if row < 0 or row >= self.rowCount():
            return
        buff_id = self._parse_leading_int(self._get_cell_text(row, 0)) or self._get_cell_text(row, 0)
        sub_id = self._parse_leading_int(self._get_cell_text(row, 1)) or self._get_cell_text(row, 1)
        desc = self.service.lookup_buff_description(buff_id, sub_id)
        self._set_desc_item(row, desc)

    def _on_buff_id_changed(self, widget: QWidget):
        row = self._row_of_widget(widget)
        if row < 0:
            return
        self._sync_subid_combo(row)
        self._refresh_row_description(row)

    def _on_subid_changed(self, widget: QWidget):
        row = self._row_of_widget(widget)
        if row >= 0:
            self._refresh_row_description(row)

    def get_rows(self) -> List[List[int]]:
        rows: List[List[int]] = []
        for r in range(self.rowCount()):
            row = []
            ok = True
            for c in range(4):
                txt = self._get_cell_text(r, c)
                if txt == "":
                    ok = False
                    break
                row.append(int(float(str(txt).split(" ", 1)[0].strip())))
            if ok:
                rows.append(row)
        return rows

    def set_rows(self, rows: List[List[Any]]):
        self.blockSignals(True)
        try:
            self.setRowCount(0)
            for row in rows:
                self.add_row(row)
        finally:
            self.blockSignals(False)
        for r in range(self.rowCount()):
            self._refresh_row_description(r)

    def add_row(self, row: Optional[List[Any]] = None):
        r = self.rowCount()
        self.insertRow(r)
        vals = row or [1, 1, 1, 1]
        buff_combo = self._create_editable_combo("ID")
        subid_combo = self._create_editable_combo("subID")
        duration_edit = self._create_line_edit("回合数")
        value_edit = self._create_line_edit("值")
        self.setCellWidget(r, 0, buff_combo)
        self.setCellWidget(r, 1, subid_combo)
        self.setCellWidget(r, 2, duration_edit)
        self.setCellWidget(r, 3, value_edit)
        self._populate_buff_id_combo(buff_combo)
        buff_combo.currentTextChanged.connect(lambda _=None, widget=buff_combo: self._on_buff_id_changed(widget))
        subid_combo.currentTextChanged.connect(lambda _=None, widget=subid_combo: self._on_subid_changed(widget))
        self._set_cell_text(r, 0, vals[0] if len(vals) > 0 else "")
        self._sync_subid_combo(r)
        self._set_cell_text(r, 1, vals[1] if len(vals) > 1 else "")
        self._set_cell_text(r, 2, vals[2] if len(vals) > 2 else "")
        self._set_cell_text(r, 3, vals[3] if len(vals) > 3 else "")
        self._set_desc_item(r, self.service.lookup_buff_description(vals[0], vals[1]))

    def delete_current_row(self):
        r = self.currentRow()
        if r < 0:
            r = self._focused_row()
        if r >= 0:
            self.removeRow(r)

    def delete_all_rows(self):
        self.setRowCount(0)


class ModifierTableWidget(QTableWidget):
    def __init__(self, key_header: str = "sub_id", value_header: str = "伤害倍率(%)"):
        super().__init__(0, 2)
        self.setHorizontalHeaderLabels([key_header, value_header])
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.setColumnWidth(0, 110)
        self.setColumnWidth(1, 110)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().setDefaultSectionSize(32)

    def _create_line_edit(self, placeholder: str, width: int) -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMaximumWidth(width)
        return edit

    def _get_cell_text(self, row: int, col: int) -> str:
        widget = self.cellWidget(row, col)
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        item = self.item(row, col)
        return item.text().strip() if item else ""

    def _set_cell_text(self, row: int, col: int, text: Any):
        widget = self.cellWidget(row, col)
        raw = str(text if text is not None else "")
        if isinstance(widget, QLineEdit):
            widget.setText(raw)
            return
        self.setItem(row, col, QTableWidgetItem(raw))

    def add_row(self, row: Optional[List[Any]] = None):
        r = self.rowCount()
        self.insertRow(r)
        vals = row or [0, 100]
        self.setCellWidget(r, 0, self._create_line_edit("ID", 96))
        self.setCellWidget(r, 1, self._create_line_edit("100", 96))
        for c, v in enumerate(vals[:2]):
            self._set_cell_text(r, c, v)

    def delete_current_row(self):
        r = self.currentRow()
        if r >= 0:
            self.removeRow(r)

    def get_rows(self) -> List[List[float]]:
        rows: List[List[float]] = []
        for r in range(self.rowCount()):
            key_txt = self._get_cell_text(r, 0)
            value_txt = self._get_cell_text(r, 1)
            if not key_txt or not value_txt:
                continue
            rows.append([int(float(key_txt)), float(value_txt)])
        return rows

    def set_rows(self, rows: List[List[Any]]):
        self.setRowCount(0)
        for row in rows:
            self.add_row(row)


class QualityEditorWidget(QWidget):
    BREAKPOINT_WIDTH = 520

    def __init__(self):
        super().__init__()
        self.values = list(QUALITY_DEFAULT)
        self.buttons: List[QPushButton] = []
        self._current_columns = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(6)
        self.grid.setVerticalSpacing(6)
        root.addLayout(self.grid)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.reset_btn = QPushButton("归零")
        self.reset_btn.clicked.connect(self.reset_values)
        btn_row.addWidget(self.reset_btn)
        root.addLayout(btn_row)

        for i, label in enumerate(QUALITY_LABELS):
            btn = QPushButton(label)
            btn.setMinimumHeight(52)
            btn.clicked.connect(lambda _=False, idx=i: self.cycle_state(idx))
            self.buttons.append(btn)

        self._relayout(force=True)
        self.refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self, force: bool = False):
        width = max(self.width(), 1)
        columns = 5 if width < self.BREAKPOINT_WIDTH else 9
        if not force and columns == self._current_columns:
            return
        self._current_columns = columns

        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                self.grid.removeWidget(widget)

        for idx, btn in enumerate(self.buttons):
            row = idx // columns
            col = idx % columns
            self.grid.addWidget(btn, row, col)

    def cycle_state(self, idx: int):
        self.values[idx] = (self.values[idx] + 2) % 3 if self.values[idx] == 1 else (1 if self.values[idx] == 2 else 2)
        self.refresh()

    def reset_values(self):
        self.values = [1] * len(self.buttons)
        self.refresh()

    def refresh(self):
        for i, btn in enumerate(self.buttons):
            state = self.values[i]
            label = QUALITY_LABELS[i]
            state_text = QUALITY_STATE_TEXT[state]
            if state == 0:
                style = (
                    "QPushButton {"
                    "border: 3px solid #c69214;"
                    "background-color: #fff4d6;"
                    "font-weight: 700;"
                    "border-radius: 8px;"
                    "padding: 6px 4px;"
                    "}"
                )
            elif state == 2:
                style = (
                    "QPushButton {"
                    "border: 3px solid #2f72d6;"
                    "background-color: #eaf2ff;"
                    "font-weight: 700;"
                    "border-radius: 8px;"
                    "padding: 6px 4px;"
                    "}"
                )
            else:
                style = (
                    "QPushButton {"
                    "border: 1px solid #b7bec8;"
                    "background-color: #f5f7fa;"
                    "font-weight: 500;"
                    "border-radius: 8px;"
                    "padding: 6px 4px;"
                    "}"
                )
            btn.setStyleSheet(style)
            btn.setText(f"{label}\n{state_text}")
            btn.setToolTip(f"{label}属性 {state_text}")

    def get_values(self) -> List[int]:
        return list(self.values)

    def set_values(self, vals: List[int]):
        vals = list(vals or [])
        self.values = (vals + [1] * 9)[:9]
        self.refresh()


class FieldBuffWidget(QGroupBox):
    def __init__(self):
        super().__init__("场地 Buff")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.addWidget(QLabel("场地倍率按百分比填写，100 表示原倍率，范围建议 0~500。"))

        self.bullet_table = self._build_section(
            root,
            "弹种伤害倍率",
            "sub_id：1=通常弹 2=镭射弹 3=体术弹 4=斩击弹 5=动能弹 6=流体弹 7=能量弹 8=御符弹 9=光弹 10=尖弹 11=追踪弹。",
            "sub_id",
            "伤害倍率(%)",
        )
        self.element_table = self._build_section(
            root,
            "属性伤害倍率",
            "sub_id：1=日 2=月 3=火 4=水 5=木 6=金 7=土 8=星 9=无。",
            "sub_id",
            "伤害倍率(%)",
        )
        self.type_table = self._build_section(
            root,
            "角色 Type 伤害倍率",
            "示例：type=1, value=5 表示该 type 造成的伤害乘以 0.05。",
            "type",
            "伤害倍率(%)",
        )

    def _build_section(self, root: QVBoxLayout, title: str, note: str, key_header: str, value_header: str) -> ModifierTableWidget:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        note_label = QLabel(note)
        note_label.setWordWrap(True)
        layout.addWidget(note_label)
        table = ModifierTableWidget(key_header, value_header)
        layout.addWidget(table)
        btns = QHBoxLayout()
        add_btn = QPushButton("添加")
        del_btn = QPushButton("删除")
        add_btn.clicked.connect(lambda: table.add_row())
        del_btn.clicked.connect(table.delete_current_row)
        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        btns.addStretch(1)
        layout.addLayout(btns)
        root.addWidget(box)
        return table

    def get_config(self) -> FieldBuffConfig:
        return FieldBuffConfig(
            bullet_type_modifiers=self.bullet_table.get_rows(),
            element_modifiers=self.element_table.get_rows(),
            type_resist_modifiers=self.type_table.get_rows(),
        )

    def set_config(self, cfg: FieldBuffConfig):
        self.bullet_table.set_rows(cfg.bullet_type_modifiers)
        self.element_table.set_rows(cfg.element_modifiers)
        self.type_table.set_rows(cfg.type_resist_modifiers)


class EnemySlotWidget(QGroupBox):
    def __init__(self, slot: int, service: DamageCalculatorService, char_index: CharacterIndex):
        super().__init__(f"敌方 {slot}")
        self.slot = slot
        self.service = service
        self.char_index = char_index
        self._build_ui()
        self._load_world_groups()

    def _build_ui(self):
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        self.enabled_check = QCheckBox("启用")
        self.enabled_check.setChecked(self.slot in (0, 2))
        self.id_edit = QLineEdit("1001")
        self.load_id_btn = QPushButton("按ID加载")
        self.load_id_btn.clicked.connect(self.on_load_by_id)
        top.addWidget(self.enabled_check)
        top.addWidget(QLabel("ID"))
        top.addWidget(self.id_edit)
        top.addWidget(self.load_id_btn)
        root.addLayout(top)

        pick = QHBoxLayout()
        self.world_combo = QComboBox()
        self.name_combo = QComboBox()
        self.world_combo.currentIndexChanged.connect(self.on_world_changed)
        self.load_name_btn = QPushButton("按世界群/名字加载")
        self.load_name_btn.clicked.connect(self.on_load_by_name)
        pick.addWidget(QLabel("世界群"))
        pick.addWidget(self.world_combo)
        pick.addWidget(QLabel("角色名"))
        pick.addWidget(self.name_combo)
        pick.addWidget(self.load_name_btn)
        root.addLayout(pick)

        form = QFormLayout()
        self.name_world_label = QLabel("- / -")
        self.name_label = QLabel("-")
        self.world_label = QLabel("-")
        self.type_label = QLabel("-")
        self.hp_spin = QSpinBox()
        self.hp_spin.setMaximum(999999999)
        self.hp_spin.setValue(50000000)
        self.yang_def_spin = QSpinBox()
        self.yang_def_spin.setMaximum(999999999)
        self.yang_def_spin.setValue(10000)
        self.yin_def_spin = QSpinBox()
        self.yin_def_spin.setMaximum(999999999)
        self.yin_def_spin.setValue(10000)
        self.barrier_spin = QSpinBox()
        self.barrier_spin.setMaximum(99)
        self.barrier_spin.setValue(9)
        self.tribe_edit = QLineEdit("")
        self.tribe_edit.textChanged.connect(self.update_tribe_description)
        self.tribe_desc_label = QLabel("-")
        self.tribe_desc_label.setWordWrap(True)
        self.tribe_desc_label.setStyleSheet("color: #5b6470;")
        self.break_check = QCheckBox("全破状态")
        self.quality_editor = QualityEditorWidget()
        form.addRow(
            _make_inline_row(
                _make_compact_field("名称", self.name_label, label_width=40, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                _make_compact_field("世界群", self.world_label, label_width=52, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                _make_compact_field("类型", self.type_label, label_width=40, widget_width=96, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                spacing=6,
            )
        )
        form.addRow("HP", self.hp_spin)
        form.addRow(
            _make_inline_row(
                _make_compact_field("阳防", self.yang_def_spin, label_width=40, widget_width=112),
                _make_compact_field("阴防", self.yin_def_spin, label_width=40, widget_width=112),
                _make_compact_field("护盾数", self.barrier_spin, label_width=52, widget_width=72),
            )
        )
        form.addRow("Quality", self.quality_editor)
        form.addRow("Tribe", self.tribe_edit)
        form.addRow("", self.tribe_desc_label)
        form.addRow("", self.break_check)
        root.addLayout(form)

        root.addWidget(QLabel("Buffs"))
        self.buff_table = BuffTableWidget(self.service)
        root.addWidget(self.buff_table)
        btns = QHBoxLayout()
        add_btn = QPushButton("添加 Buff")
        del_btn = QPushButton("删除 Buff")
        clear_btn = QPushButton("删除全部 Buff")
        add_btn.clicked.connect(lambda: self.buff_table.add_row())
        del_btn.clicked.connect(self.buff_table.delete_current_row)
        clear_btn.clicked.connect(self.buff_table.delete_all_rows)
        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        btns.addWidget(clear_btn)
        btns.addStretch(1)
        root.addLayout(btns)
    def _load_world_groups(self):
        self.world_combo.blockSignals(True)
        self.world_combo.clear()
        self.world_combo.addItems(self.char_index.get_world_groups())
        self.world_combo.blockSignals(False)
        self.on_world_changed()

    def on_world_changed(self):
        rows = self.char_index.get_rows_by_world(self.world_combo.currentText().strip())
        self.name_combo.clear()
        for row in rows:
            self.name_combo.addItem(f"{row['name']} [{row['id']}]", row["id"])

    def on_load_by_id(self):
        try:
            self._apply_meta(self.service.load_character_meta(int(self.id_edit.text().strip())))
        except Exception as e:
            QMessageBox.critical(self, f"鍔犺浇鏁屾柟 {self.slot} 澶辫触", str(e))

    def on_load_by_name(self):
        try:
            cid = self.name_combo.currentData()
            if cid is None:
                raise RuntimeError("褰撳墠涓栫晫缇や笅娌℃湁瑙掕壊")
            self.id_edit.setText(str(cid))
            self._apply_meta(self.service.load_character_meta(int(cid)))
        except Exception as e:
            QMessageBox.critical(self, f"鍔犺浇鏁屾柟 {self.slot} 澶辫触", str(e))

    def update_tribe_description(self):
        self.tribe_desc_label.setText(self.service.describe_tribe_text(self.tribe_edit.text()))

    def _apply_meta(self, meta: Dict[str, Any]):
        self.name_world_label.setText(f"{meta.get('name', '')} / {meta.get('world_group', '')}")
        self.name_label.setText(str(meta.get("name", "") or "-"))
        self.world_label.setText(str(meta.get("world_group", "") or "-"))
        self.type_label.setText(str(meta.get("type_label", "")))
        self.tribe_edit.setText(",".join(str(x) for x in (meta.get("tribe", []) or [])))
        self.update_tribe_description()

    def get_config(self) -> EnemySlotConfig:
        return EnemySlotConfig(
            enabled=self.enabled_check.isChecked(),
            character_id=int(self.id_edit.text().strip()),
            hp=int(self.hp_spin.value()),
            yang_def=int(self.yang_def_spin.value()),
            yin_def=int(self.yin_def_spin.value()),
            barrier_count=int(self.barrier_spin.value()),
            quality=self.quality_editor.get_values(),
            tribe_text=self.tribe_edit.text().strip(),
            is_break_all=self.break_check.isChecked(),
            buffs=self.buff_table.get_rows(),
        )

    def apply_config(self, cfg: EnemySlotConfig):
        self.enabled_check.setChecked(cfg.enabled)
        self.id_edit.setText(str(cfg.character_id))
        try:
            self._apply_meta(self.service.load_character_meta(int(cfg.character_id)))
        except Exception:
            pass
        self.hp_spin.setValue(int(cfg.hp))
        self.yang_def_spin.setValue(int(cfg.yang_def))
        self.yin_def_spin.setValue(int(cfg.yin_def))
        self.barrier_spin.setValue(int(cfg.barrier_count))
        self.quality_editor.set_values(cfg.quality)
        self.tribe_edit.setText(cfg.tribe_text)
        self.update_tribe_description()
        self.break_check.setChecked(bool(cfg.is_break_all))
        self.buff_table.set_rows(cfg.buffs)


class EquipmentRowWidget(QWidget):
    DISPLAY_LABELS = {
        "1a": "符卡1-1",
        "2a": "符卡2-1",
        "1b": "符卡1-2",
        "2b": "符卡2-2",
        "5": "LW",
    }

    def __init__(self, slot_key: str, service: DamageCalculatorService, character_id_getter):
        super().__init__()
        self.slot_key = slot_key
        self.service = service
        self.character_id_getter = character_id_getter
        self._build_ui()
        self._load_options()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(6)

        self.slot_label = QLabel(self.DISPLAY_LABELS.get(self.slot_key, self.slot_key))
        self.slot_label.setFixedWidth(56)
        self.id_edit = QLineEdit("")
        self.id_edit.setPlaceholderText("ID")
        self.id_edit.setMaximumWidth(72)
        self.name_combo = QComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.setInsertPolicy(QComboBox.NoInsert)
        self.name_combo.setMaximumWidth(192)

        id_btn = QPushButton("按ID")
        name_btn = QPushButton("按名称")
        rec_btn = QPushButton("推荐")
        clear_btn = QPushButton("清空")
        for btn in (id_btn, name_btn, rec_btn, clear_btn):
            btn.setFixedWidth(54)
        id_btn.clicked.connect(self.apply_by_id)
        name_btn.clicked.connect(self.apply_by_name)
        rec_btn.clicked.connect(self.apply_recommended)
        clear_btn.clicked.connect(self.clear_selection)

        top.addWidget(self.slot_label)
        top.addWidget(self.id_edit)
        top.addWidget(self.name_combo, 0, Qt.AlignLeft)
        top.addWidget(id_btn)
        top.addWidget(name_btn)
        top.addWidget(rec_btn)
        top.addWidget(clear_btn)
        top.addStretch(1)
        root.addLayout(top)

        self.desc_label = QLabel("无绘卷")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #5b6470;")
        root.addWidget(self.desc_label)

    def _load_options(self):
        self.name_combo.blockSignals(True)
        self.name_combo.clear()
        for label, equipment_id in self.service.list_equipment_options():
            self.name_combo.addItem(label, equipment_id)
        self.name_combo.blockSignals(False)

    def apply_by_id(self):
        equipment = self.service.get_equipment(self.id_edit.text().strip())
        if not equipment:
            QMessageBox.information(self, "提示", "未找到对应绘卷 ID")
            return
        self.set_equipment_id(int(equipment["equipment_id"]))

    def apply_by_name(self):
        equipment = self.service.resolve_equipment_by_text(self.name_combo.currentText())
        if not equipment:
            QMessageBox.information(self, "提示", "未找到对应绘卷名称")
            return
        self.set_equipment_id(int(equipment["equipment_id"]))

    def apply_recommended(self):
        try:
            char_id = int(self.character_id_getter())
        except Exception:
            QMessageBox.information(self, "提示", "请先填写角色 ID")
            return
        equipment_id = self.service.get_recommended_equipment_id(char_id, self.slot_key)
        if equipment_id <= 0:
            QMessageBox.information(self, "提示", "没有可用的推荐绘卷")
            return
        self.set_equipment_id(equipment_id)

    def clear_selection(self):
        self.id_edit.setText("")
        self.name_combo.setCurrentIndex(-1)
        self.name_combo.setEditText("")
        self.desc_label.setText("无绘卷效果")
        self.desc_label.show()

    def set_equipment_id(self, equipment_id: int):
        equipment = self.service.get_equipment(equipment_id)
        if not equipment:
            self.clear_selection()
            return
        text = f"[{equipment['equipment_id']}] {equipment['name']}"
        idx = self.name_combo.findText(text)
        self.id_edit.setText(str(equipment["equipment_id"]))
        if idx >= 0:
            self.name_combo.setCurrentIndex(idx)
        else:
            self.name_combo.setEditText(text)
        desc = self.service.describe_equipment_text(equipment_id)
        self.desc_label.setText(desc.split(" | ", 1)[1] if " | " in desc else desc)
        self.desc_label.show()

    def get_equipment_id(self) -> int:
        try:
            return int(self.id_edit.text().strip())
        except Exception:
            return 0


class AllySlotWidget(QGroupBox):
    DEFAULT_CHARACTER_IDS = (1001, 1002, 1003)
    ATTACK_TYPE_DISPLAY = {
        "1": "1符",
        "1c": "扩散",
        "2": "2符",
        "2c": "集中",
        "5": "终符",
    }

    def __init__(self, slot: int, service: DamageCalculatorService, char_index: CharacterIndex):
        super().__init__(f"我方 {slot}")
        self.slot = slot
        self.service = service
        self.char_index = char_index
        self._build_ui()
        self._load_world_groups()

    def _build_ui(self):
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        self.enabled_check = QCheckBox("启用")
        self.enabled_check.setChecked(self.slot == 0)
        self.id_edit = QLineEdit(str(self.DEFAULT_CHARACTER_IDS[self.slot] if self.slot < len(self.DEFAULT_CHARACTER_IDS) else 1001))
        self.load_id_btn = QPushButton("按ID加载")
        self.load_id_btn.clicked.connect(self.on_load_by_id)
        top.addWidget(self.enabled_check)
        top.addWidget(QLabel("ID"))
        top.addWidget(self.id_edit)
        top.addWidget(self.load_id_btn)
        root.addLayout(top)

        pick = QHBoxLayout()
        self.world_combo = QComboBox()
        self.name_combo = QComboBox()
        self.world_combo.currentIndexChanged.connect(self.on_world_changed)
        self.load_name_btn = QPushButton("按世界群/名字加载")
        self.load_name_btn.clicked.connect(self.on_load_by_name)
        pick.addWidget(QLabel("世界群"))
        pick.addWidget(self.world_combo)
        pick.addWidget(QLabel("角色名"))
        pick.addWidget(self.name_combo)
        pick.addWidget(self.load_name_btn)
        root.addLayout(pick)

        form = QFormLayout()
        self.name_world_label = QLabel("- / -")
        self.name_label = QLabel("-")
        self.world_label = QLabel("-")
        self.type_label = QLabel("-")
        self.attack_type_combo = QComboBox()
        self.initial_spirit_spin = QDoubleSpinBox()
        self.initial_spirit_spin.setDecimals(1)
        self.initial_spirit_spin.setMaximum(10.0)
        self.initial_spirit_spin.setValue(3.0)
        self.barrier_spin = QSpinBox()
        self.barrier_spin.setMaximum(99)
        self.barrier_spin.setValue(5)
        self.skill_order_edit = QLineEdit("0,1,2")
        self.shield_open_spin = QSpinBox()
        self.shield_open_spin.setMaximum(99)
        self.shield_open_spin.setValue(DEFAULT_SHIELD_OPEN_COUNT)
        self.spirit_level_spin = QSpinBox()
        self.spirit_level_spin.setMaximum(5)
        self.spirit_level_spin.setValue(DEFAULT_SPIRIT_LEVEL)
        self.target_enemy_combo = QComboBox()
        self.target_enemy_combo.addItem("位置0", 0)
        self.target_enemy_combo.addItem("位置1", 1)
        self.target_enemy_combo.addItem("位置2", 2)
        self.equipment_rows = {
            "1a": EquipmentRowWidget("1a", self.service, self._current_character_id_text),
            "2a": EquipmentRowWidget("2a", self.service, self._current_character_id_text),
            "1b": EquipmentRowWidget("1b", self.service, self._current_character_id_text),
            "2b": EquipmentRowWidget("2b", self.service, self._current_character_id_text),
            "5": EquipmentRowWidget("5", self.service, self._current_character_id_text),
        }
        equipment_box = QGroupBox("")
        equipment_layout = QVBoxLayout(equipment_box)
        equipment_layout.setContentsMargins(6, 6, 6, 6)
        equipment_layout.setSpacing(6)
        equipment_note = QLabel("按 5 张符卡位配置：符卡1-1、符卡2-1、符卡1-2、符卡2-2、LW。普通攻击 1c / 2c 不使用绘卷。")
        equipment_note.setWordWrap(True)
        equipment_note.setStyleSheet("color: #5b6470;")
        equipment_layout.addWidget(equipment_note)
        for key in ("1a", "2a", "1b", "2b", "5"):
            equipment_layout.addWidget(self.equipment_rows[key])
        form.addRow(
            _make_inline_row(
                _make_compact_field("名称", self.name_label, label_width=40, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                _make_compact_field("世界群", self.world_label, label_width=52, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                _make_compact_field("类型", self.type_label, label_width=40, widget_width=90, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                _make_compact_field("攻击类型", self.attack_type_combo, label_width=62, widget_width=108, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                spacing=6,
            )
        )
        form.addRow(equipment_box)
        form.addRow(
            _make_inline_row(
                _make_compact_field("初始p点", self.initial_spirit_spin, label_width=56, widget_width=92),
                _make_compact_field("初始护盾数", self.barrier_spin, label_width=62, widget_width=72),
                spacing=6,
            )
        )
        form.addRow("技能顺序(逗号)", self.skill_order_edit)
        form.addRow(
            _make_inline_row(
                _make_compact_field("目标敌人", self.target_enemy_combo, label_width=56, widget_width=92),
                _make_compact_field("开p数", self.spirit_level_spin, label_width=44, widget_width=72),
                _make_compact_field("开盾数量", self.shield_open_spin, label_width=56, widget_width=72),
                spacing=6,
            )
        )
        root.addLayout(form)

        root.addWidget(QLabel("Buffs"))
        self.buff_table = BuffTableWidget(self.service)
        root.addWidget(self.buff_table)
        btns = QHBoxLayout()
        add_btn = QPushButton("添加 Buff")
        del_btn = QPushButton("删除 Buff")
        clear_btn = QPushButton("删除全部 Buff")
        add_btn.clicked.connect(lambda: self.buff_table.add_row())
        del_btn.clicked.connect(self.buff_table.delete_current_row)
        clear_btn.clicked.connect(self.buff_table.delete_all_rows)
        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        btns.addWidget(clear_btn)
        btns.addStretch(1)
        root.addLayout(btns)

    def _fallback_character_id(self) -> int:
        if 0 <= self.slot < len(self.DEFAULT_CHARACTER_IDS):
            return int(self.DEFAULT_CHARACTER_IDS[self.slot])
        return 1001

    def _current_character_id(self) -> int:
        text = self.id_edit.text().strip()
        if not text:
            return self._fallback_character_id()
        try:
            return int(float(text))
        except Exception:
            return self._fallback_character_id()

    def _current_character_id_text(self) -> str:
        return str(self._current_character_id())
    def _load_world_groups(self):
        self.world_combo.blockSignals(True)
        self.world_combo.clear()
        self.world_combo.addItems(self.char_index.get_world_groups())
        self.world_combo.blockSignals(False)
        self.on_world_changed()

    def on_world_changed(self):
        rows = self.char_index.get_rows_by_world(self.world_combo.currentText().strip())
        self.name_combo.clear()
        for row in rows:
            self.name_combo.addItem(f"{row['name']} [{row['id']}]", row["id"])

    def on_load_by_id(self):
        try:
            cid = self._current_character_id()
            self.id_edit.setText(str(cid))
            self._apply_meta(self.service.load_character_meta(cid))
        except Exception as e:
            QMessageBox.critical(self, f"鍔犺浇鎴戞柟 {self.slot} 澶辫触", str(e))

    def on_load_by_name(self):
        try:
            cid = self.name_combo.currentData()
            if cid is None:
                raise RuntimeError("褰撳墠涓栫晫缇や笅娌℃湁瑙掕壊")
            self.id_edit.setText(str(cid))
            self._apply_meta(self.service.load_character_meta(int(cid)))
        except Exception as e:
            QMessageBox.critical(self, f"鍔犺浇鎴戞柟 {self.slot} 澶辫触", str(e))

    def _apply_meta(self, meta: Dict[str, Any]):
        self.name_world_label.setText(f"{meta.get('name', '')} / {meta.get('world_group', '')}")
        self.name_label.setText(str(meta.get("name", "") or "-"))
        self.world_label.setText(str(meta.get("world_group", "") or "-"))
        self.type_label.setText(str(meta.get("type_label", "")))
        self.attack_type_combo.clear()
        attack_types = meta.get("available_attack_types", []) or []
        for attack_type in attack_types:
            attack_type_text = str(attack_type)
            self.attack_type_combo.addItem(self.ATTACK_TYPE_DISPLAY.get(attack_type_text, attack_type_text), attack_type_text)
        if DEFAULT_ATTACK_TYPE in attack_types:
            idx = self.attack_type_combo.findData(DEFAULT_ATTACK_TYPE)
            if idx >= 0:
                self.attack_type_combo.setCurrentIndex(idx)

    def get_config(self) -> AllySlotConfig:
        return AllySlotConfig(
            enabled=self.enabled_check.isChecked(),
            character_id=self._current_character_id(),
            initial_spirit=float(self.initial_spirit_spin.value()),
            barrier_count=int(self.barrier_spin.value()),
            skill_order_text=self.skill_order_edit.text().strip(),
            shield_open_count=int(self.shield_open_spin.value()),
            attack_type=str(self.attack_type_combo.currentData() or self.attack_type_combo.currentText().strip() or DEFAULT_ATTACK_TYPE),
            spirit_level=int(self.spirit_level_spin.value()),
            target_enemy_pos=int(self.target_enemy_combo.currentData() if self.target_enemy_combo.currentData() is not None else 0),
            buffs=self.buff_table.get_rows(),
            equipment_ids={key: row.get_equipment_id() for key, row in self.equipment_rows.items()},
        )

    def apply_config(self, cfg: AllySlotConfig):
        self.enabled_check.setChecked(cfg.enabled)
        self.id_edit.setText(str(cfg.character_id))
        self.initial_spirit_spin.setValue(float(cfg.initial_spirit))
        self.barrier_spin.setValue(int(cfg.barrier_count))
        self.skill_order_edit.setText(cfg.skill_order_text)
        self.shield_open_spin.setValue(int(cfg.shield_open_count))
        self.spirit_level_spin.setValue(int(cfg.spirit_level))
        idx = self.target_enemy_combo.findData(int(cfg.target_enemy_pos))
        self.target_enemy_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.buff_table.set_rows(cfg.buffs)
        for key, row in self.equipment_rows.items():
            row.set_equipment_id(int((cfg.equipment_ids or {}).get(key, 0) or 0))
        try:
            meta = self.service.load_character_meta(int(cfg.character_id))
            self._apply_meta(meta)
            idx = self.attack_type_combo.findData(str(cfg.attack_type))
            if idx >= 0:
                self.attack_type_combo.setCurrentIndex(idx)
        except Exception:
            pass


class SortableTableItem(QTableWidgetItem):
    def __init__(self, text: str, sort_value: Any = None):
        super().__init__(text)
        self.sort_value = text if sort_value is None else sort_value

    def __lt__(self, other):
        if isinstance(other, SortableTableItem):
            return self.sort_value < other.sort_value
        return super().__lt__(other)


class CheckOptionGroup(QWidget):
    def __init__(self, options: List[tuple[int, str]], columns: int = 4):
        super().__init__()
        self._checkboxes: List[tuple[int, QCheckBox]] = []
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(6)
        for idx, (value, label) in enumerate(options):
            checkbox = QCheckBox(label)
            layout.addWidget(checkbox, idx // max(columns, 1), idx % max(columns, 1))
            self._checkboxes.append((int(value), checkbox))

    def selected_values(self) -> List[int]:
        return [value for value, checkbox in self._checkboxes if checkbox.isChecked()]

    def clear_selection(self):
        blockers = [QSignalBlocker(checkbox) for _value, checkbox in self._checkboxes]
        for _value, checkbox in self._checkboxes:
            checkbox.setChecked(False)
        del blockers


class CollapsibleSection(QWidget):
    def __init__(self, title: str, content: QWidget, *, expanded: bool = True):
        super().__init__()
        self.content = content
        self.toggle_btn = QToolButton()
        self.toggle_btn.setText(title)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(expanded)
        self.toggle_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_btn.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self.toggle_btn.clicked.connect(self._sync_state)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)
        root.addWidget(self.toggle_btn)
        root.addWidget(self.content)

        self._sync_state()

    def _sync_state(self):
        expanded = self.toggle_btn.isChecked()
        self.toggle_btn.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self.content.setVisible(expanded)

    def set_title(self, title: str):
        self.toggle_btn.setText(title)


class CharacterQueryWidget(QWidget):
    def __init__(self, service: DamageCalculatorService, open_character_callback):
        super().__init__()
        self.service = service
        self.open_character_callback = open_character_callback
        self._build_ui()
        self.run_search()

    def _build_ui(self):
        root = QVBoxLayout(self)

        filter_box = QGroupBox("筛选")
        filter_layout = QGridLayout(filter_box)

        type_options: List[tuple[int, str]] = []
        for type_id, label in TYPE_LABELS.items():
            type_options.append((type_id, label))
        self.type_group = CheckOptionGroup(type_options, columns=4)

        element_options: List[tuple[int, str]] = []
        for raw_id, label in ELEMENT_RAW_LABELS.items():
            if raw_id <= 0:
                continue
            element_options.append((raw_id, label))
        self.element_group = CheckOptionGroup(element_options, columns=4)

        bullet_options: List[tuple[int, str]] = []
        for raw_id, label in BULLET_RAW_LABELS.items():
            if raw_id <= 0:
                continue
            bullet_options.append((raw_id, label))
        self.bullet_group = CheckOptionGroup(bullet_options, columns=4)

        self.killer_edit = QLineEdit()
        self.killer_edit.setPlaceholderText("输入 tribe 名称/ID，或用右侧下拉追加，多个请用逗号分隔")
        self.killer_combo = QComboBox()
        self.killer_combo.addItem("选择特攻", 0)
        for tribe_id, tribe_name in self.service.get_tribe_options():
            self.killer_combo.addItem(f"{tribe_name} ({tribe_id})", tribe_id)
        self.killer_add_btn = QPushButton("添加")
        self.killer_clear_btn = QPushButton("清空")
        self.killer_add_btn.clicked.connect(self._append_killer_filter)
        self.killer_clear_btn.clicked.connect(lambda: self.killer_edit.clear())

        self.world_group_edit = QLineEdit()
        self.world_group_edit.setPlaceholderText("输入世界群，或用右侧下拉追加，多个请用逗号分隔")
        self.world_group_combo = QComboBox()
        self.world_group_combo.addItem("选择世界群", "")
        for world_group in self.service.get_world_group_options():
            self.world_group_combo.addItem(world_group, world_group)
        self.world_group_add_btn = QPushButton("添加")
        self.world_group_clear_btn = QPushButton("清空")
        self.world_group_add_btn.clicked.connect(self._append_world_group_filter)
        self.world_group_clear_btn.clicked.connect(lambda: self.world_group_edit.clear())

        self.re_combo = QComboBox()
        self.re_combo.addItems(["全部", "是", "否"])

        search_btn = QPushButton("查询")
        reset_btn = QPushButton("重置")
        search_btn.clicked.connect(self.run_search)
        reset_btn.clicked.connect(self.reset_filters)

        filter_layout.addWidget(QLabel("Type"), 0, 0)
        filter_layout.addWidget(self.type_group, 0, 1, 1, 5)
        filter_layout.addWidget(QLabel("转生"), 1, 0)
        filter_layout.addWidget(self.re_combo, 1, 1)
        filter_layout.addWidget(search_btn, 1, 4)
        filter_layout.addWidget(reset_btn, 1, 5)

        filter_layout.addWidget(QLabel("终符属性"), 2, 0)
        filter_layout.addWidget(self.element_group, 2, 1, 1, 5)
        filter_layout.addWidget(QLabel("终符弹种"), 3, 0)
        filter_layout.addWidget(self.bullet_group, 3, 1, 1, 5)
        filter_layout.addWidget(QLabel("特攻"), 4, 0)
        filter_layout.addWidget(self.killer_edit, 4, 1, 1, 2)
        filter_layout.addWidget(self.killer_combo, 4, 3)
        filter_layout.addWidget(self.killer_add_btn, 4, 4)
        filter_layout.addWidget(self.killer_clear_btn, 4, 5)
        filter_layout.addWidget(QLabel("世界群"), 5, 0)
        filter_layout.addWidget(self.world_group_edit, 5, 1, 1, 2)
        filter_layout.addWidget(self.world_group_combo, 5, 3)
        filter_layout.addWidget(self.world_group_add_btn, 5, 4)
        filter_layout.addWidget(self.world_group_clear_btn, 5, 5)
        root.addWidget(CollapsibleSection("筛选条件", filter_box, expanded=False))

        self.result_table = QTableWidget(0, 10)
        self.result_table.setHorizontalHeaderLabels(["ID", "名称", "世界群", "Type", "阳攻", "阳防", "阴攻", "阴防", "速度", "终符属性"])
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.result_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.result_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.result_table.setSortingEnabled(True)
        header = self.result_table.horizontalHeader()
        header.setMinimumSectionSize(1)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        for col in range(4, 9):
            header.setSectionResizeMode(col, QHeaderView.Fixed)
        header.setSectionResizeMode(9, QHeaderView.Stretch)
        self.result_table.setColumnWidth(0, 44)
        self.result_table.setColumnWidth(2, 52)
        self.result_table.setColumnWidth(3, 48)
        for col in range(4, 9):
            self.result_table.setColumnWidth(col, 48)
        self.result_table.cellClicked.connect(self._on_cell_clicked)
        root.addWidget(self.result_table)

    def reset_filters(self):
        self.setUpdatesEnabled(False)
        blockers = [
            QSignalBlocker(self.killer_combo),
            QSignalBlocker(self.world_group_combo),
            QSignalBlocker(self.re_combo),
        ]
        try:
            self.type_group.clear_selection()
            self.element_group.clear_selection()
            self.bullet_group.clear_selection()
            self.killer_edit.clear()
            self.killer_combo.setCurrentIndex(0)
            self.world_group_edit.clear()
            self.world_group_combo.setCurrentIndex(0)
            self.re_combo.setCurrentIndex(0)
        finally:
            del blockers
            self.setUpdatesEnabled(True)
        self.run_search()

    def run_search(self):
        rows = self.service.search_characters(
            type_values=self.type_group.selected_values(),
            element_values=self.element_group.selected_values(),
            bullet_values=self.bullet_group.selected_values(),
            killer_tribes=self.service.parse_tribe_filter_text(self.killer_edit.text()),
            world_groups=self.service.parse_world_group_filter_text(self.world_group_edit.text()),
            re_only=self.re_combo.currentText() if self.re_combo.currentIndex() > 0 else "",
        )
        self.result_table.setSortingEnabled(False)
        self.result_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.result_table.setItem(r, 0, SortableTableItem(str(row["character_id"]), int(row["character_id"])))
            name_item = SortableTableItem(str(row["name"]), str(row["name"]))
            name_item.setData(Qt.UserRole, int(row["character_id"]))
            self.result_table.setItem(r, 1, name_item)
            self.result_table.setItem(r, 2, SortableTableItem(str(row["world_group"]), str(row["world_group"])))
            self.result_table.setItem(r, 3, SortableTableItem(str(row["type_label"]), str(row["type_label"])))
            self.result_table.setItem(r, 4, SortableTableItem(str(row["yang_atk"]), int(row["yang_atk"])))
            self.result_table.setItem(r, 5, SortableTableItem(str(row["yang_def"]), int(row["yang_def"])))
            self.result_table.setItem(r, 6, SortableTableItem(str(row["yin_atk"]), int(row["yin_atk"])))
            self.result_table.setItem(r, 7, SortableTableItem(str(row["yin_def"]), int(row["yin_def"])))
            self.result_table.setItem(r, 8, SortableTableItem(str(row["speed"]), int(row["speed"])))
            self.result_table.setItem(r, 9, SortableTableItem(str(row["attack5_element_sequence"]), str(row["attack5_element_sequence"])))
        self.result_table.setSortingEnabled(True)
        self.result_table.sortItems(1, Qt.AscendingOrder)
        self.result_table.resizeRowsToContents()

    def _on_cell_clicked(self, row: int, column: int):
        if column != 1:
            return
        item = self.result_table.item(row, 1)
        if item is None:
            return
        char_id = item.data(Qt.UserRole)
        if char_id:
            self.open_character_callback(int(char_id))

    def _append_killer_filter(self):
        tribe_id = self.killer_combo.currentData()
        label = self.killer_combo.currentText().strip()
        if not tribe_id:
            return
        existing_ids = set(self.service.parse_tribe_filter_text(self.killer_edit.text()))
        if int(tribe_id) in existing_ids:
            return
        parts = [part.strip() for part in self.killer_edit.text().split(",") if part.strip()]
        parts.append(label)
        self.killer_edit.setText(", ".join(parts))

    def _append_world_group_filter(self):
        world_group = str(self.world_group_combo.currentData() or "").strip()
        if not world_group:
            return
        existing = set(self.service.parse_world_group_filter_text(self.world_group_edit.text()))
        if world_group in existing:
            return
        parts = [part.strip() for part in self.world_group_edit.text().split(",") if part.strip()]
        parts.append(world_group)
        self.world_group_edit.setText(", ".join(parts))


class CharacterDetailWidget(QWidget):
    def __init__(self, service: DamageCalculatorService):
        super().__init__()
        self.service = service
        self.current_char_id: Optional[int] = None
        self.is_editing = False
        self.attack_detail_views: List[QPlainTextEdit] = []
        self.skill_sections: List[CollapsibleSection] = []
        self.skill_views: List[QPlainTextEdit] = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        top_box = QGroupBox("角色详情")
        top_layout = QHBoxLayout(top_box)

        self.avatar_label = QLabel("暂无头像\nPNG 预留区")
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setFixedSize(220, 220)
        self.avatar_label.setStyleSheet("border: 1px dashed #9aa5b1; background: #f7f9fb; color: #5b6470;")
        top_layout.addWidget(self.avatar_label)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(6)
        self.info_name = QLabel("-")
        self.info_name_raw = QLabel("-")
        self.info_subname = QLabel("-")
        self.info_world = QLabel("-")
        self.info_type = QLabel("-")
        self.info_re = QLabel("-")
        self.info_hp = QLabel("-")
        self.info_yang_atk = QLabel("-")
        self.info_yang_def = QLabel("-")
        self.info_yin_atk = QLabel("-")
        self.info_yin_def = QLabel("-")
        self.info_speed = QLabel("-")
        self.info_tribe = QLabel("-")
        self.info_tribe.setWordWrap(True)
        info_layout.addWidget(_make_inline_row(_make_compact_field("名称", self.info_name, label_width=40, label_align=Qt.AlignLeft | Qt.AlignVCenter), _make_compact_field("原名", self.info_name_raw, label_width=40, label_align=Qt.AlignLeft | Qt.AlignVCenter), spacing=10))
        info_layout.addWidget(_make_inline_row(_make_compact_field("称号", self.info_subname, label_width=40, label_align=Qt.AlignLeft | Qt.AlignVCenter), spacing=10))
        info_layout.addWidget(
            _make_inline_row(
                _make_compact_field("世界群", self.info_world, label_width=52, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                _make_compact_field("Type", self.info_type, label_width=40, widget_width=96, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                _make_compact_field("转生", self.info_re, label_width=40, widget_width=60, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                spacing=10,
            )
        )
        info_layout.addWidget(
            _make_inline_row(
                _make_compact_field("HP", self.info_hp, label_width=32, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                _make_compact_field("阳攻", self.info_yang_atk, label_width=40, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                _make_compact_field("阳防", self.info_yang_def, label_width=40, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                spacing=10,
            )
        )
        info_layout.addWidget(
            _make_inline_row(
                _make_compact_field("阴攻", self.info_yin_atk, label_width=40, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                _make_compact_field("阴防", self.info_yin_def, label_width=40, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                _make_compact_field("速度", self.info_speed, label_width=40, label_align=Qt.AlignLeft | Qt.AlignVCenter),
                spacing=10,
            )
        )
        info_layout.addWidget(_make_inline_row(_make_compact_field("Tribe", self.info_tribe, label_width=44, label_align=Qt.AlignLeft | Qt.AlignVCenter), spacing=10))
        top_layout.addLayout(info_layout, 1)
        root.addWidget(CollapsibleSection("基础信息", top_box, expanded=True))

        self.attack_box = QWidget()
        self.attack_layout = QVBoxLayout(self.attack_box)
        self.attack_layout.setContentsMargins(0, 0, 0, 0)
        self.attack_layout.setSpacing(6)
        self.attack_layout.setAlignment(Qt.AlignTop)
        self.attack_sections: List[CollapsibleSection] = []
        root.addWidget(CollapsibleSection("攻击详情", self.attack_box, expanded=True))

        self.passive_box = QGroupBox("特性")
        passive_layout = QVBoxLayout(self.passive_box)
        self.passive_text = QPlainTextEdit()
        self.passive_text.setReadOnly(True)
        passive_layout.addWidget(self.passive_text)
        root.addWidget(CollapsibleSection("特性", self.passive_box, expanded=True))

        self.skill_box = QGroupBox("技能")
        skill_layout = QHBoxLayout(self.skill_box)
        skill_layout.setContentsMargins(6, 4, 6, 4)
        skill_layout.setSpacing(6)
        skill_layout.setAlignment(Qt.AlignTop)
        for idx in range(3):
            skill_content = QPlainTextEdit()
            skill_content.setReadOnly(True)
            skill_content.setMaximumBlockCount(32)
            skill_content.setFixedHeight(72)
            section = CollapsibleSection(f"技能{idx + 1}", skill_content, expanded=False)
            section.toggle_btn.setMinimumHeight(24)
            section.toggle_btn.setMaximumHeight(24)
            section.toggle_btn.setStyleSheet("padding: 1px 4px;")
            skill_layout.addWidget(section, 1)
            self.skill_sections.append(section)
            self.skill_views.append(skill_content)
        root.addWidget(CollapsibleSection("技能", self.skill_box, expanded=True))

        btns = QHBoxLayout()
        self.edit_btn = QPushButton("修改")
        self.save_btn = QPushButton("保存")
        self.discard_btn = QPushButton("放弃修改")
        self.edit_btn.clicked.connect(self.start_edit)
        self.save_btn.clicked.connect(self.save_changes)
        self.discard_btn.clicked.connect(self.discard_changes)
        btns.addWidget(self.edit_btn)
        btns.addWidget(self.save_btn)
        btns.addWidget(self.discard_btn)
        btns.addStretch(1)
        root.addLayout(btns)

        self.raw_editor = QPlainTextEdit()
        self.raw_editor.setReadOnly(True)
        root.addWidget(CollapsibleSection("原始数据", self.raw_editor, expanded=False), 1)

    def load_character(self, char_id: int):
        self.deactivate()
        payload = self.service.get_character_detail_payload(int(char_id))
        self.current_char_id = int(char_id)
        self._apply_payload(payload)

    def _apply_payload(self, payload: Dict[str, Any]):
        self.info_name.setText(str(payload.get("name", "")))
        self.info_name_raw.setText(str(payload.get("name_raw", "")))
        self.info_subname.setText(str(payload.get("subname", "")))
        self.info_world.setText(str(payload.get("world_group", "")))
        self.info_type.setText(str(payload.get("type_label", "")))
        self.info_re.setText("是" if payload.get("re") else "否")
        self.info_hp.setText(str(payload.get("hp", 0)))
        self.info_yang_atk.setText(str(payload.get("yang_atk", 0)))
        self.info_yang_def.setText(str(payload.get("yang_def", 0)))
        self.info_yin_atk.setText(str(payload.get("yin_atk", 0)))
        self.info_yin_def.setText(str(payload.get("yin_def", 0)))
        self.info_speed.setText(str(payload.get("speed", 0)))
        self.info_tribe.setText(str(payload.get("tribe_text", "-")))
        self.raw_editor.setPlainText(str(payload.get("raw_json_text", "")))
        self.raw_editor.setReadOnly(True)
        self.is_editing = False
        self.passive_text.setPlainText("\n\n".join(payload.get("passive_entries", []) or []))
        skill_entries = list(payload.get("skill_entries", []) or [])
        for idx, section in enumerate(self.skill_sections):
            entry = skill_entries[idx] if idx < len(skill_entries) else {}
            title = str(entry.get("title", f"技能{idx + 1}"))
            content = str(entry.get("content", "-"))
            section.set_title(title)
            self.skill_views[idx].setPlainText(content)
        self.attack_detail_views = []
        while self.attack_layout.count():
            item = self.attack_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.attack_sections = []
        for section in list(payload.get("attack_sections", []) or []):
            text = QPlainTextEdit()
            text.setReadOnly(True)
            text.setFixedHeight(360)
            text.setPlainText(str(section.get("content", "")))
            panel = CollapsibleSection(f"{section.get('title', '')} | {section.get('name', '')}", text, expanded=False)
            self.attack_layout.addWidget(panel)
            self.attack_sections.append(panel)
            self.attack_detail_views.append(text)
        self.attack_layout.addStretch(1)

        avatar_path = payload.get("avatar_path")
        if avatar_path:
            pixmap = QPixmap(str(avatar_path))
            if not pixmap.isNull():
                self.avatar_label.setPixmap(pixmap.scaled(self.avatar_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.avatar_label.setText("")
            else:
                self.avatar_label.setPixmap(QPixmap())
                self.avatar_label.setText("头像读取失败")
        else:
            self.avatar_label.setPixmap(QPixmap())
            self.avatar_label.setText("暂无头像\nPNG 预留区")

    def start_edit(self):
        if self.current_char_id is None:
            return
        self.raw_editor.setReadOnly(False)
        self.is_editing = True

    def save_changes(self):
        if self.current_char_id is None:
            return
        try:
            payload = json.loads(self.raw_editor.toPlainText())
            self.service.save_character_full(self.current_char_id, payload)
            self.load_character(self.current_char_id)
            QMessageBox.information(self, "保存成功", "角色数据已保存。")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def discard_changes(self):
        if self.current_char_id is None:
            self.raw_editor.clear()
            self.raw_editor.setReadOnly(True)
            self.is_editing = False
            return
        payload = self.service.get_character_detail_payload(self.current_char_id)
        self._apply_payload(payload)

    def deactivate(self):
        if self.is_editing:
            self.discard_changes()


class EquipmentQueryWidget(QWidget):
    STYLE_LABELS = {0: "D", 1: "梅", 2: "兰", 3: "菊", 4: "竹"}
    TARGET_LABELS = {1: "自身", 2: "己方全体", 3: "敌方单体", 4: "敌方全体"}

    def __init__(self, service: DamageCalculatorService):
        super().__init__()
        self.service = service
        self._rows_cache: Dict[tuple, List[Dict[str, Any]]] = {}
        self._build_ui()
        self.run_search()

    def _build_ui(self):
        root = QVBoxLayout(self)

        filter_box = QGroupBox("筛选")
        filter_layout = QVBoxLayout(filter_box)

        top = QGridLayout()
        self.star_combo = QComboBox()
        self.star_combo.addItem("全部", 0)
        for star in range(1, 6):
            self.star_combo.addItem(f"{star}星", star)

        self.style_combo = QComboBox()
        self.style_combo.addItem("全部", -1)
        for code, label in self.STYLE_LABELS.items():
            self.style_combo.addItem(label, code)

        self.stat1_combo = QComboBox()
        self.stat2_combo = QComboBox()
        for combo in (self.stat1_combo, self.stat2_combo):
            combo.addItem("全部", "")
            for key, label in self.service.STAT_KEY_LABELS.items():
                combo.addItem(label, key)

        top.addWidget(QLabel("星级"), 0, 0)
        top.addWidget(self.star_combo, 0, 1)
        top.addWidget(QLabel("种类"), 0, 2)
        top.addWidget(self.style_combo, 0, 3)
        top.addWidget(QLabel("属性1"), 0, 4)
        top.addWidget(self.stat1_combo, 0, 5)
        top.addWidget(QLabel("属性2"), 0, 6)
        top.addWidget(self.stat2_combo, 0, 7)
        filter_layout.addLayout(top)

        self.buff_id_combos: List[QComboBox] = []
        self.buff_subid_edits: List[QLineEdit] = []
        self.buff_subid_combos: List[QComboBox] = []
        self.buff_subid_add_buttons: List[QPushButton] = []
        self.buff_target_combos: List[QComboBox] = []
        self.buff_type_edits: List[QLineEdit] = []
        self.buff_type_combos: List[QComboBox] = []
        self.buff_type_add_buttons: List[QPushButton] = []
        self.buff_value_edits: List[QLineEdit] = []
        for idx in range(3):
            row = QGridLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setHorizontalSpacing(6)
            row.setVerticalSpacing(4)
            row.addWidget(QLabel(f"Buff{idx + 1}"), 0, 0, 2, 1, Qt.AlignTop)
            id_combo = QComboBox()
            id_combo.setMinimumWidth(110)
            id_combo.setMaximumWidth(130)
            id_combo.addItem("全部", 0)
            for buff_id, label in self.service.list_equipment_buff_id_options():
                id_combo.addItem(f"{buff_id} {label}", buff_id)
            subid_edit = QLineEdit()
            subid_edit.setPlaceholderText("subID 多选")
            subid_edit.setMinimumWidth(120)
            subid_combo = QComboBox()
            subid_combo.setMinimumWidth(90)
            subid_combo.setMaximumWidth(110)
            subid_combo.addItem("选择 subID", 0)
            subid_add_btn = QPushButton("添加")
            subid_add_btn.setMaximumWidth(56)
            subid_add_btn.clicked.connect(lambda _=False, row_idx=idx: self._append_subid_filter(row_idx))
            target_combo = QComboBox()
            target_combo.setMinimumWidth(110)
            target_combo.addItem("全部", 0)
            for key, label in self.TARGET_LABELS.items():
                target_combo.addItem(label, key)
            type_edit = QLineEdit()
            type_edit.setPlaceholderText("type 多选")
            type_edit.setMinimumWidth(120)
            type_combo = QComboBox()
            type_combo.setMinimumWidth(90)
            type_combo.setMaximumWidth(110)
            type_combo.addItem("选择 type", 0)
            for type_id, label in sorted(TYPE_LABELS.items()):
                type_combo.addItem(f"{type_id} {label}", type_id)
            type_add_btn = QPushButton("添加")
            type_add_btn.setMaximumWidth(56)
            type_add_btn.clicked.connect(lambda _=False, row_idx=idx: self._append_type_filter(row_idx))
            value_edit = QLineEdit()
            value_edit.setPlaceholderText("值")
            value_edit.setMinimumWidth(110)
            value_edit.setMaximumWidth(160)
            id_combo.currentIndexChanged.connect(lambda _=0, row_idx=idx: self._sync_subid_options(row_idx))
            id_combo.currentIndexChanged.connect(lambda _=0, row_idx=idx: self._sync_type_controls(row_idx))
            row.addWidget(id_combo, 0, 1)
            row.addWidget(subid_edit, 0, 2)
            row.addWidget(subid_combo, 0, 3)
            row.addWidget(subid_add_btn, 0, 4)
            row.addWidget(target_combo, 0, 5)
            row.addWidget(value_edit, 1, 1)
            row.addWidget(type_edit, 1, 2)
            row.addWidget(type_combo, 1, 3)
            row.addWidget(type_add_btn, 1, 4)
            row.setColumnStretch(2, 1)
            row.setColumnStretch(5, 1)
            filter_layout.addLayout(row)
            self.buff_id_combos.append(id_combo)
            self.buff_subid_edits.append(subid_edit)
            self.buff_subid_combos.append(subid_combo)
            self.buff_subid_add_buttons.append(subid_add_btn)
            self.buff_target_combos.append(target_combo)
            self.buff_type_edits.append(type_edit)
            self.buff_type_combos.append(type_combo)
            self.buff_type_add_buttons.append(type_add_btn)
            self.buff_value_edits.append(value_edit)
            self._sync_subid_options(idx)
            self._sync_type_controls(idx)

        btns = QHBoxLayout()
        search_btn = QPushButton("查询")
        reset_btn = QPushButton("重置")
        search_btn.clicked.connect(self.run_search)
        reset_btn.clicked.connect(self.reset_filters)
        btns.addWidget(search_btn)
        btns.addWidget(reset_btn)
        btns.addStretch(1)
        filter_layout.addLayout(btns)

        root.addWidget(CollapsibleSection("筛选条件", filter_box, expanded=False))

        self.result_table = QTableWidget(0, 8)
        self.result_table.setHorizontalHeaderLabels(["ID", "名称", "星级", "种类", "属性", "Buff1", "Buff2", "Buff3"])
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.result_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.result_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.result_table.setSortingEnabled(True)
        header = self.result_table.horizontalHeader()
        header.setMinimumSectionSize(1)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Stretch)
        self.result_table.setColumnWidth(0, 56)
        self.result_table.setColumnWidth(2, 36)
        self.result_table.setColumnWidth(3, 36)
        self.result_table.setColumnWidth(4, 72)
        root.addWidget(self.result_table)

    def _sync_subid_options(self, idx: int):
        buff_id = self.buff_id_combos[idx].currentData()
        combo = self.buff_subid_combos[idx]
        current = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("选择 subID", 0)
        if buff_id:
            for sub_id, label in self.service.list_equipment_buff_subid_options(buff_id):
                combo.addItem(f"{sub_id} {label}", sub_id)
        match_idx = combo.findData(current)
        combo.setCurrentIndex(match_idx if match_idx >= 0 else 0)
        combo.blockSignals(False)

    def _sync_type_controls(self, idx: int):
        buff_id = int(self.buff_id_combos[idx].currentData() or 0)
        enabled = buff_id in (1, 2)
        self.buff_type_edits[idx].setEnabled(enabled)
        self.buff_type_combos[idx].setEnabled(enabled)
        self.buff_type_add_buttons[idx].setEnabled(enabled)
        if not enabled:
            self.buff_type_edits[idx].clear()
            self.buff_type_combos[idx].setCurrentIndex(0)

    @staticmethod
    def _parse_multi_select_text(text: str, label_map: Optional[Dict[str, int]] = None) -> List[int]:
        values: List[int] = []
        seen = set()
        for part in str(text or "").replace("，", ",").split(","):
            token = part.strip()
            if not token:
                continue
            parsed: Optional[int] = None
            lead = token.split(" ", 1)[0].strip()
            if lead.isdigit():
                parsed = int(lead)
            elif label_map:
                parsed = label_map.get(token)
            if parsed is None or parsed in seen:
                continue
            seen.add(parsed)
            values.append(parsed)
        return values

    def _append_combo_value(self, edit: QLineEdit, combo: QComboBox):
        text = combo.currentText().strip()
        data = combo.currentData()
        if not data or not text:
            return
        existing = [part.strip() for part in edit.text().replace("，", ",").split(",") if part.strip()]
        if text in existing:
            return
        existing.append(text)
        edit.setText(", ".join(existing))

    def _append_subid_filter(self, idx: int):
        self._append_combo_value(self.buff_subid_edits[idx], self.buff_subid_combos[idx])

    def _append_type_filter(self, idx: int):
        self._append_combo_value(self.buff_type_edits[idx], self.buff_type_combos[idx])

    def _current_filter_key(self) -> tuple:
        buff_key = []
        for idx in range(3):
            buff_key.append(
                (
                    int(self.buff_id_combos[idx].currentData() or 0),
                    tuple(self._parse_multi_select_text(self.buff_subid_edits[idx].text())),
                    int(self.buff_target_combos[idx].currentData() or 0),
                    tuple(self._parse_multi_select_text(self.buff_type_edits[idx].text(), {label: value for value, label in TYPE_LABELS.items()})),
                    self.buff_value_edits[idx].text().strip(),
                )
            )
        return (
            int(self.star_combo.currentData() or 0),
            int(self.style_combo.currentData() or 0),
            str(self.stat1_combo.currentData() or ""),
            str(self.stat2_combo.currentData() or ""),
            tuple(buff_key),
        )

    def _effect_matches_filter(self, effect: Dict[str, Any], filter_item: Dict[str, Any]) -> bool:
        if not effect or bool(effect.get("ignored", False)):
            return False
        buff_id_filter = int(filter_item.get("buff_id", 0) or 0)
        sub_id_filters = [int(v) for v in (filter_item.get("sub_ids", []) or []) if int(v) > 0]
        target_filter = int(filter_item.get("target_type", 0) or 0)
        type_filters = [int(v) for v in (filter_item.get("type_conditions", []) or []) if int(v) > 0]
        value_filter_text = str(filter_item.get("value", "") or "").strip()
        if buff_id_filter and int(effect.get("buff_id", 0) or 0) != buff_id_filter:
            return False
        if sub_id_filters and int(effect.get("sub_id", 0) or 0) not in sub_id_filters:
            return False
        if target_filter and int(effect.get("target_type", 0) or 0) != target_filter:
            return False
        if type_filters and buff_id_filter in (1, 2):
            if int(effect.get("condition_type", 0) or 0) not in type_filters:
                return False
        if value_filter_text:
            try:
                expected = float(value_filter_text)
                actual = float(effect.get("value", 0) or 0)
            except Exception:
                return False
            if abs(actual - expected) > 1e-9:
                return False
        return True

    def _cell_label(self, text: str, highlighted: bool) -> QWidget:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(0)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(label)
        if highlighted:
            frame.setStyleSheet("QFrame { border: 2px solid #111; } QLabel { font-weight: 700; border: none; }")
        else:
            frame.setStyleSheet("QFrame { border: none; } QLabel { border: none; }")
        return frame

    def _set_result_rows(self, rows: List[Dict[str, Any]]):
        active_buff_filters = []
        for idx in range(3):
            raw_id = self.buff_id_combos[idx].currentData()
            raw_subids = self._parse_multi_select_text(self.buff_subid_edits[idx].text())
            target = self.buff_target_combos[idx].currentData()
            type_conditions = self._parse_multi_select_text(self.buff_type_edits[idx].text(), {label: value for value, label in TYPE_LABELS.items()})
            value = self.buff_value_edits[idx].text().strip()
            if not raw_id and not raw_subids and not target and not type_conditions and not value:
                continue
            active_buff_filters.append(
                {
                    "buff_id": raw_id,
                    "sub_ids": raw_subids,
                    "target_type": target,
                    "type_conditions": type_conditions,
                    "value": value,
                }
            )
        self.result_table.setUpdatesEnabled(False)
        self.result_table.setSortingEnabled(False)
        try:
            self.result_table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                self.result_table.setItem(r, 0, SortableTableItem(str(row["equipment_id"]), int(row["equipment_id"])))
                self.result_table.setItem(r, 1, SortableTableItem(str(row["name"]), str(row["name"])))
                self.result_table.setItem(r, 2, SortableTableItem(str(row["stars"]), int(row["stars"])))
                self.result_table.setItem(r, 3, SortableTableItem(str(row["style_label"]), str(row["style_label"])))
                self.result_table.setItem(r, 4, SortableTableItem(str(row["stats_text"]), str(row["stats_text"])))
                for col_idx, text_key in enumerate(("buff_1_text", "buff_2_text", "buff_3_text"), start=5):
                    effect_idx = col_idx - 5
                    effect = ((row.get("raw_effects", []) or []) + [{}, {}, {}])[effect_idx]
                    highlighted = bool(active_buff_filters) and any(self._effect_matches_filter(effect, item) for item in active_buff_filters)
                    text = str(row[text_key])
                    self.result_table.setItem(r, col_idx, SortableTableItem("", text))
                    self.result_table.setCellWidget(r, col_idx, self._cell_label(text, highlighted))
        finally:
            self.result_table.resizeRowsToContents()
            self.result_table.setSortingEnabled(True)
            self.result_table.sortItems(1, Qt.AscendingOrder)
            self.result_table.setUpdatesEnabled(True)

    def reset_filters(self):
        self.setUpdatesEnabled(False)
        blockers = [
            QSignalBlocker(self.star_combo),
            QSignalBlocker(self.style_combo),
            QSignalBlocker(self.stat1_combo),
            QSignalBlocker(self.stat2_combo),
        ]
        for idx in range(3):
            blockers.append(QSignalBlocker(self.buff_id_combos[idx]))
            blockers.append(QSignalBlocker(self.buff_subid_edits[idx]))
            blockers.append(QSignalBlocker(self.buff_target_combos[idx]))
            blockers.append(QSignalBlocker(self.buff_type_edits[idx]))
            blockers.append(QSignalBlocker(self.buff_type_combos[idx]))
            blockers.append(QSignalBlocker(self.buff_value_edits[idx]))
        try:
            self.star_combo.setCurrentIndex(0)
            self.style_combo.setCurrentIndex(0)
            self.stat1_combo.setCurrentIndex(0)
            self.stat2_combo.setCurrentIndex(0)
            for idx in range(3):
                self.buff_id_combos[idx].setCurrentIndex(0)
                self._sync_subid_options(idx)
                self.buff_subid_edits[idx].clear()
                self.buff_subid_combos[idx].setCurrentIndex(0)
                self.buff_target_combos[idx].setCurrentIndex(0)
                self.buff_type_edits[idx].clear()
                self.buff_type_combos[idx].setCurrentIndex(0)
                self.buff_value_edits[idx].clear()
                self._sync_type_controls(idx)
        finally:
            del blockers
            self.setUpdatesEnabled(True)
        default_key = self._current_filter_key()
        cached_rows = self._rows_cache.get(default_key)
        if cached_rows is not None:
            self._set_result_rows(cached_rows)
            return
        self.run_search()

    def run_search(self):
        filter_key = self._current_filter_key()
        cached_rows = self._rows_cache.get(filter_key)
        if cached_rows is not None:
            self._set_result_rows(cached_rows)
            return

        buff_filters = []
        for idx in range(3):
            raw_id = self.buff_id_combos[idx].currentData()
            raw_subids = self._parse_multi_select_text(self.buff_subid_edits[idx].text())
            target = self.buff_target_combos[idx].currentData()
            type_conditions = self._parse_multi_select_text(self.buff_type_edits[idx].text(), {label: value for value, label in TYPE_LABELS.items()})
            if not raw_id and not raw_subids and not target and not type_conditions:
                if not self.buff_value_edits[idx].text().strip():
                    continue
            buff_filters.append(
                {
                    "buff_id": raw_id,
                    "sub_ids": raw_subids,
                    "target_type": target,
                    "type_conditions": type_conditions,
                    "value": self.buff_value_edits[idx].text().strip(),
                }
            )
        stat_filters = [self.stat1_combo.currentData(), self.stat2_combo.currentData()]
        rows = self.service.search_equipment(
            stars=self.star_combo.currentData(),
            style_code=self.style_combo.currentData(),
            buff_filters=buff_filters,
            stat_filters=stat_filters,
        )
        self._rows_cache[filter_key] = rows
        self._set_result_rows(rows)

