from __future__ import annotations

import argparse
import copy
import csv
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from dataclasses import asdict, is_dataclass
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

from arena_excel_parser import ensure_arena_enemy_data, find_arena_xlsx, write_arena_outputs
from combat_constants import (
    BULLET_RAW_LABELS,
    DEFAULT_ALLY_ID,
    DEFAULT_ATTACK_TYPE,
    DEFAULT_ENEMY_ID,
    DEFAULT_SHIELD_OPEN_COUNT,
    DEFAULT_SPIRIT_LEVEL,
    DEFAULT_TARGET_ENEMY_POS,
    ELEMENT_RAW_LABELS,
    QUALITY_DEFAULT,
    QUALITY_LABELS,
    QUALITY_STATE_TEXT,
    TYPE_LABELS,
)
from gui.config import AllySlotConfig, EnemySlotConfig, FieldBuffConfig, ProcessConfig
from gui.resources import ROOT_DIR
from gui.services import CharacterIndex, DamageCalculatorService
from vs_lua_parser import ensure_vs_json


BASE_DIR = Path(__file__).resolve().parent
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else BASE_DIR
WEB_DIR = BASE_DIR / "web"
ASSET_DIR = BASE_DIR / "assets"
AVATAR_DIR = ASSET_DIR / "avatars"
PRESET_DIR = APP_DIR / "presets"
CHARACTER_PRESET_PATH = PRESET_DIR / "character_presets.json"
CHARACTER_PRESET_DIR = PRESET_DIR / "character_presets"
ARENA_PRESET_PATH = PRESET_DIR / "arena_presets.json"
ARENA_DATA_JSON_PATH = PRESET_DIR / "arena_enemy_data.json"
ARENA_DATA_CSV_PATH = PRESET_DIR / "arena_enemy_data.csv"
VS_PRESET_DIR = PRESET_DIR / "vs"
VS_LUA_SOURCE_CANDIDATES = [
    BASE_DIR.parent / "复灵敌人数据06-19.lua",
    BASE_DIR / "复灵敌人数据06-19.lua",
    APP_DIR / "_internal" / "复灵敌人数据06-19.lua",
]
VS_JSON_PATH = VS_PRESET_DIR / "vs_enemy_data_06-19.json"
OUTPUT_DIR = APP_DIR / "output"
LOG_PATH = APP_DIR / "app.log"

ARENA_FIXED_LUNATIC_HP = {
    1: {1: 67499, 2: 74999, 3: 82499},
    2: {1: 33749, 2: 37499, 3: 41249},
    3: {1: 22499, 2: 24999, 3: 27499},
}
ARENA_SHEET_TO_KEY = {"周擂台1": "weekly1", "周擂台2": "weekly2"}
ARENA_KEY_TO_SHEET = {"weekly1": "周擂台1", "weekly2": "周擂台2"}


SUMMARY_COLUMN_LABELS = {
    "character_id": "角色ID",
    "character_name": "原名",
    "name_cn": "名称",
    "world_group": "世界群",
    "character_type": "类型",
    "attack_type": "攻击类型",
    "equipment_id": "绘卷ID",
    "equipment_name": "绘卷名称",
    "skill_order": "技能顺序",
    "spirit_level": "开p数",
    "target_enemy_pos": "目标敌人",
    "enemy_pos_0_total": "敌方0伤害",
    "enemy_pos_1_total": "敌方1伤害",
    "enemy_pos_2_total": "敌方2伤害",
    "overall_total": "总伤害",
    "yang_damage_total": "阳伤害",
    "yin_damage_total": "阴伤害",
    "enemy_pos_0_weak_seg_count": "敌方0弱点段数",
    "enemy_pos_0_killer_seg_count": "敌方0特攻段数",
    "enemy_pos_1_weak_seg_count": "敌方1弱点段数",
    "enemy_pos_1_killer_seg_count": "敌方1特攻段数",
    "enemy_pos_2_weak_seg_count": "敌方2弱点段数",
    "enemy_pos_2_killer_seg_count": "敌方2特攻段数",
    "status": "状态",
    "reason": "原因",
    "seg0": "第一段",
    "seg1": "第二段",
    "seg2": "第三段",
    "seg3": "第四段",
    "seg4": "第五段",
    "seg5": "第六段",
    "yang_ratio": "阳占比",
    "yin_ratio": "阴占比",
    "yinyang_role": "阴阳定位",
}

SUMMARY_COLUMN_ORDER = [
    "character_id",
    "name_cn",
    "world_group",
    "character_type",
    "attack_type",
    "equipment_id",
    "equipment_name",
    "skill_order",
    "spirit_level",
    "target_enemy_pos",
    "enemy_pos_0_total",
    "enemy_pos_1_total",
    "enemy_pos_2_total",
    "overall_total",
    "yang_damage_total",
    "yin_damage_total",
    "enemy_pos_0_weak_seg_count",
    "enemy_pos_0_killer_seg_count",
    "enemy_pos_1_weak_seg_count",
    "enemy_pos_1_killer_seg_count",
    "enemy_pos_2_weak_seg_count",
    "enemy_pos_2_killer_seg_count",
    "status",
    "reason",
    "seg0",
    "seg1",
    "seg2",
    "seg3",
    "seg4",
    "seg5",
    "yang_ratio",
    "yin_ratio",
    "yinyang_role",
]


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "__dict__"):
        return _jsonable(vars(value))
    return value


def _log(message: str) -> None:
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass


def _read_json_body(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _ensure_runtime_dirs() -> None:
    PRESET_DIR.mkdir(parents=True, exist_ok=True)
    VS_PRESET_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _load_json_file(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        _log(f"failed to load json {path}: {exc}")
        return default


def _save_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def _load_character_presets() -> Dict[str, Any]:
    presets: Dict[str, Any] = {}
    legacy = _load_json_file(CHARACTER_PRESET_PATH, {})
    if isinstance(legacy, dict):
        presets.update({str(k): v for k, v in legacy.items() if isinstance(v, dict)})
    if CHARACTER_PRESET_DIR.exists():
        for path in sorted(CHARACTER_PRESET_DIR.glob("*.json")):
            try:
                payload = _load_json_file(path, {})
                if isinstance(payload, dict):
                    char_id = str(payload.get("character_id") or path.stem)
                    presets[char_id] = payload
            except Exception as exc:
                _log(f"failed to load character preset {path}: {exc}")
    return presets


def _save_character_presets(presets: Dict[str, Any]) -> None:
    CHARACTER_PRESET_DIR.mkdir(parents=True, exist_ok=True)
    normalized: Dict[str, Any] = {}
    for raw_id, preset in (presets or {}).items():
        char_id = str(raw_id).strip()
        if not char_id or not isinstance(preset, dict):
            continue
        payload = dict(preset)
        payload["character_id"] = int(char_id) if char_id.isdigit() else char_id
        normalized[char_id] = payload
        _save_json_file(CHARACTER_PRESET_DIR / f"{char_id}.json", payload)
    _save_json_file(CHARACTER_PRESET_PATH, normalized)


def _arena_section_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "stat_overrides": {
            "yang_atk": _to_int(row.get("yang_atk"), 0),
            "yang_def": _to_int(row.get("yang_def"), 0),
            "yin_atk": _to_int(row.get("yin_atk"), 0),
            "yin_def": _to_int(row.get("yin_def"), 0),
            "speed": _to_int(row.get("speed"), 0),
        },
        "barrier_count": _to_int(row.get("barrier_count"), 7),
        "quality": row.get("quality") or [1] * 9,
        "enemy_skill_effects": row.get("skill_effects") or row.get("enemy_skill_effects") or [],
    }


def _swap_yinyang_section(section: Dict[str, Any]) -> Dict[str, Any]:
    src = section or {}
    stats = dict(src.get("stat_overrides") or {})
    swapped = dict(src)
    swapped["stat_overrides"] = {
        "yang_atk": _to_int(stats.get("yin_atk"), 0),
        "yang_def": _to_int(stats.get("yin_def"), 0),
        "yin_atk": _to_int(stats.get("yang_atk"), 0),
        "yin_def": _to_int(stats.get("yang_def"), 0),
        "speed": _to_int(stats.get("speed"), 0),
    }
    return swapped


def _normalize_arena_preset(char_id: Any, preset: Dict[str, Any]) -> Dict[str, Any]:
    raw = preset if isinstance(preset, dict) else {}
    normalized = {
        "character_id": _to_int(raw.get("character_id", char_id), _to_int(char_id, 0)),
        "name": raw.get("name", ""),
        "world_group": raw.get("world_group", ""),
        "type_label": raw.get("type_label", ""),
    }
    weekly1 = raw.get("weekly1")
    weekly2 = raw.get("weekly2")
    if not isinstance(weekly1, dict) and isinstance(raw.get("stat_overrides"), dict):
        weekly1 = {
            "stat_overrides": raw.get("stat_overrides") or {},
            "barrier_count": raw.get("barrier_count", 7),
            "quality": raw.get("quality") or [1] * 9,
            "enemy_skill_effects": raw.get("enemy_skill_effects") or [],
        }
    if isinstance(weekly1, dict):
        normalized["weekly1"] = weekly1
    if isinstance(weekly2, dict):
        normalized["weekly2"] = weekly2
    if "weekly1" in normalized and "weekly2" not in normalized:
        normalized["weekly2"] = _swap_yinyang_section(normalized["weekly1"])
    if "weekly2" in normalized and "weekly1" not in normalized:
        normalized["weekly1"] = _swap_yinyang_section(normalized["weekly2"])
    return normalized


def _load_arena_presets() -> Dict[str, Any]:
    presets: Dict[str, Any] = {}
    source = find_arena_xlsx(BASE_DIR)
    if source:
        try:
            payload = ensure_arena_enemy_data(source, ARENA_DATA_CSV_PATH, ARENA_DATA_JSON_PATH)
            for row in payload.get("rows", []):
                char_id = _to_int(row.get("character_id"), 0)
                if char_id <= 0:
                    continue
                key = str(char_id)
                if key not in presets:
                    presets[key] = {
                        "character_id": char_id,
                        "name": row.get("name", ""),
                    }
                sheet_key = ARENA_SHEET_TO_KEY.get(str(row.get("sheet", "")))
                if sheet_key:
                    presets[key][sheet_key] = _arena_section_from_row(row)
            for key, preset in list(presets.items()):
                presets[key] = _normalize_arena_preset(key, preset)
        except Exception as exc:
            _log(f"failed to build arena presets from xlsx: {exc}")
    saved = _load_json_file(ARENA_PRESET_PATH, {})
    if isinstance(saved, dict):
        for key, value in saved.items():
            if isinstance(value, dict):
                presets[str(key)] = _normalize_arena_preset(key, value)
    return presets


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except Exception:
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "是", "启用"}


def _split_values(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value).replace("，", ",").split(",") if part.strip()]


def _enemy_config_from_payload(raw: Optional[Dict[str, Any]]) -> EnemySlotConfig:
    raw = raw or {}
    return EnemySlotConfig(
        enabled=_to_bool(raw.get("enabled", False)),
        character_id=_to_int(raw.get("character_id"), DEFAULT_ENEMY_ID),
        hp=_to_int(raw.get("hp"), 50_000_000),
        yang_atk=_to_int(raw.get("yang_atk"), 0),
        yang_def=_to_int(raw.get("yang_def"), 10_000),
        yin_atk=_to_int(raw.get("yin_atk"), 0),
        yin_def=_to_int(raw.get("yin_def"), 10_000),
        speed=_to_int(raw.get("speed"), 0),
        barrier_count=_to_int(raw.get("barrier_count"), 9),
        quality=[_to_int(v, 1) for v in (raw.get("quality") or QUALITY_DEFAULT)],
        tribe_text=str(raw.get("tribe_text", "") or ""),
        is_break_all=_to_bool(raw.get("is_break_all", False)),
        buffs=raw.get("buffs") or [],
        enemy_skill_effects=raw.get("enemy_skill_effects") or [],
    )


def _ally_config_from_payload(raw: Optional[Dict[str, Any]]) -> AllySlotConfig:
    raw = raw or {}
    return AllySlotConfig(
        enabled=_to_bool(raw.get("enabled", False)),
        character_id=_to_int(raw.get("character_id"), DEFAULT_ALLY_ID),
        initial_spirit=_to_float(raw.get("initial_spirit"), 3.0),
        barrier_count=_to_int(raw.get("barrier_count"), 5),
        skill_order_text=str(raw.get("skill_order_text", "") or ""),
        shield_open_count=_to_int(raw.get("shield_open_count"), DEFAULT_SHIELD_OPEN_COUNT),
        attack_type=str(raw.get("attack_type", DEFAULT_ATTACK_TYPE) or DEFAULT_ATTACK_TYPE),
        spirit_level=_to_int(raw.get("spirit_level"), DEFAULT_SPIRIT_LEVEL),
        target_enemy_pos=_to_int(raw.get("target_enemy_pos"), DEFAULT_TARGET_ENEMY_POS),
        buffs=raw.get("buffs") or [],
        equipment_ids=raw.get("equipment_ids") or {},
    )


def _configs_from_payload(payload: Dict[str, Any]) -> Tuple[Dict[int, EnemySlotConfig], Dict[int, AllySlotConfig], ProcessConfig]:
    enemies_raw = payload.get("enemy_slots") or {}
    if str(payload.get("mode", "default")) == "arena":
        waves_raw = payload.get("enemy_waves") or {}
        current_wave = _to_int(payload.get("current_wave", payload.get("wave_count", 1)), 1)
        enemies_raw = waves_raw.get(str(current_wave)) or waves_raw.get(current_wave) or enemies_raw
    allies_raw = payload.get("ally_slots") or {}
    enemy_slots = {
        pos: _enemy_config_from_payload(enemies_raw.get(str(pos)) or enemies_raw.get(pos) or {})
        for pos in range(3)
    }
    ally_slots = {
        pos: _ally_config_from_payload(allies_raw.get(str(pos)) or allies_raw.get(pos) or {})
        for pos in range(3)
    }
    process_config = ProcessConfig.from_payload(payload.get("process") or {})
    return enemy_slots, ally_slots, process_config


def _extract_character_presets(payload: Dict[str, Any]) -> Dict[str, Any]:
    presets = payload.get("character_presets") or payload.get("role_presets") or {}
    return presets if isinstance(presets, dict) else {}


def _write_summary_csv(rows: List[Dict[str, Any]]) -> str:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    headers = [SUMMARY_COLUMN_LABELS.get(key, key) for key in SUMMARY_COLUMN_ORDER]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([row.get(key, "") for key in SUMMARY_COLUMN_ORDER])
    return str(path)


def _arena_section_to_row(char_id: str, preset: Dict[str, Any], sheet: str, section: Dict[str, Any], existing: Dict[str, Any] | None = None) -> Dict[str, Any]:
    stats = section.get("stat_overrides") or {}
    row = dict(existing or {})
    row.pop("arena_enemy_id", None)
    row.update(
        {
            "sheet": sheet,
            "character_id": _to_int(char_id, _to_int(preset.get("character_id"), 0)),
            "name": preset.get("name") or row.get("name") or str(char_id),
            "yang_atk": _to_int(stats.get("yang_atk"), 0),
            "yang_def": _to_int(stats.get("yang_def"), 0),
            "yin_atk": _to_int(stats.get("yin_atk"), 0),
            "yin_def": _to_int(stats.get("yin_def"), 0),
            "speed": _to_int(stats.get("speed"), 0),
            "barrier_count": _to_int(section.get("barrier_count"), 7),
            "quality": section.get("quality") or row.get("quality") or [1] * 9,
            "skill_effects": section.get("enemy_skill_effects") or [],
        }
    )
    return row


def _sync_arena_data_from_presets(presets: Dict[str, Any]) -> None:
    source = find_arena_xlsx(BASE_DIR)
    if source:
        payload = ensure_arena_enemy_data(source, ARENA_DATA_CSV_PATH, ARENA_DATA_JSON_PATH)
    else:
        payload = _load_json_file(ARENA_DATA_JSON_PATH, {"parser_version": 5, "rows": []})
    rows = [dict(row) for row in (payload.get("rows") or []) if isinstance(row, dict)]
    index = {(str(row.get("character_id", "")), str(row.get("sheet", ""))): row for row in rows}
    for raw_id, raw_preset in (presets or {}).items():
        if not isinstance(raw_preset, dict):
            continue
        preset = _normalize_arena_preset(raw_id, raw_preset)
        for section_key, sheet in ARENA_KEY_TO_SHEET.items():
            section = preset.get(section_key)
            if not isinstance(section, dict):
                continue
            idx_key = (str(_to_int(raw_id, _to_int(preset.get("character_id"), 0))), sheet)
            new_row = _arena_section_to_row(idx_key[0], preset, sheet, section, index.get(idx_key))
            if idx_key in index:
                index[idx_key].clear()
                index[idx_key].update(new_row)
            else:
                rows.append(new_row)
                index[idx_key] = new_row
    payload["rows"] = rows
    write_arena_outputs(payload, ARENA_DATA_CSV_PATH, ARENA_DATA_JSON_PATH)


def _enrich_vs_enemy(enemy: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(enemy, dict):
        return enemy
    for key in ("skill_buffs", "ex1_buffs", "ex2_buffs"):
        enemy[f"{key}_text"] = STATE.service.format_runtime_effect_list(enemy.get(key) or [])
    enemy["card_buffs_text"] = [
        STATE.service.format_runtime_effect_list(rows)
        for rows in (enemy.get("card_buffs") or [])
        if isinstance(rows, list)
    ]
    if enemy.get("tribe_ids"):
        enemy["tribe_text_ids"] = ",".join(str(v) for v in enemy.get("tribe_ids") or [])
    return enemy


def _enrich_vs_preset(preset: Dict[str, Any]) -> Dict[str, Any]:
    row = copy.deepcopy(preset)
    card_id = _to_int(row.get("card_id"), 0)
    if card_id > 0 and card_id < 10000:
        summary = STATE.service.get_equipment_summary(card_id)
        if summary:
            row["drop_card"] = summary
    for item in row.get("enemies", []) or []:
        _enrich_vs_enemy(item.get("enemy"))
        for phase in item.get("phases", []) or []:
            _enrich_vs_enemy(phase)
    return row


class AppState:
    def __init__(self):
        self.service = DamageCalculatorService()
        self.character_index = CharacterIndex()

    def character_options(self, query: str = "", limit: int = 80) -> List[Dict[str, Any]]:
        q = str(query or "").strip().lower()
        rows: List[Dict[str, Any]] = []
        for cid in self.service.discover_all_ids():
            try:
                meta = self.service.load_character_meta(cid)
                raw_data = self.service.load_character_full(cid)
            except Exception:
                continue
            raw_info = raw_data.get("character_info", {}) or {}
            raw_name = str(raw_info.get("name", "") or meta.get("name", "") or "")
            name = self.service.translate_character_name(raw_name, cid)
            world = str(meta.get("world_group", "") or "")
            haystack = f"{cid} {name} {raw_name} {world}".lower()
            if q and q not in haystack:
                continue
            rows.append(
                {
                    "id": int(cid),
                    "name": name,
                    "world_group": world,
                    "type_label": meta.get("type_label", ""),
                    "label": f"{cid} | {name} | {world}",
                }
            )
            if len(rows) >= limit:
                break
        return rows

    def resolve_character(self, query: Any) -> Optional[Dict[str, Any]]:
        text = str(query or "").strip()
        if not text:
            return None
        try:
            meta = self.service.load_character_meta(int(float(text)))
            meta["name"] = self.service.translate_character_name(meta.get("name", ""), int(meta["id"]))
            return meta
        except Exception:
            pass
        lowered = text.lower()
        for option in self.character_options("", limit=100000):
            if lowered in str(option.get("name", "")).lower() or lowered in str(option.get("world_group", "")).lower():
                meta = self.service.load_character_meta(int(option["id"]))
                meta["name"] = self.service.translate_character_name(meta.get("name", ""), int(option["id"]))
                return meta
        return None


STATE = AppState()


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "lwMAA-v1.2"

    def log_message(self, format: str, *args: Any) -> None:
        message = "[server] " + format % args
        _log(message)
        try:
            sys.stderr.write(message + "\n")
        except Exception:
            pass

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(_jsonable(payload), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, exc: Exception, status: int = 500) -> None:
        _log(str(exc))
        _log(traceback.format_exc())
        self._send_json(
            {
                "ok": False,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
            status=status,
        )

    def _send_static(self, path: str) -> None:
        rel = unquote(path.lstrip("/")) or "index.html"
        if rel == "":
            rel = "index.html"
        if rel.startswith("web/"):
            rel = rel[4:]
        target = (WEB_DIR / rel).resolve()
        web_root = WEB_DIR.resolve()
        if not str(target).startswith(str(web_root)) or not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_asset(self, path: str) -> None:
        rel = unquote(path.lstrip("/"))
        if rel.startswith("assets/"):
            rel = rel[len("assets/") :]
        target = (ASSET_DIR / rel).resolve()
        asset_root = ASSET_DIR.resolve()
        fallback = (AVATAR_DIR / "S0.png").resolve()
        if not str(target).startswith(str(asset_root)) or not target.exists() or not target.is_file():
            if "avatars/" in rel and fallback.exists():
                target = fallback
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/bootstrap":
                return self._api_bootstrap()
            if parsed.path == "/api/character-options":
                params = parse_qs(parsed.query)
                return self._send_json({"ok": True, "data": STATE.character_options((params.get("q") or [""])[0])})
            if parsed.path == "/api/character-resolve":
                params = parse_qs(parsed.query)
                meta = STATE.resolve_character((params.get("q") or [""])[0])
                return self._send_json({"ok": True, "data": meta})
            if parsed.path == "/api/equipment-resolve":
                params = parse_qs(parsed.query)
                return self._send_json({"ok": True, "data": STATE.service.get_equipment_summary((params.get("q") or [""])[0])})
            if parsed.path == "/api/characters":
                return self._api_search_characters(parse_qs(parsed.query))
            if parsed.path.startswith("/api/characters/"):
                char_id = _to_int(parsed.path.rsplit("/", 1)[-1])
                return self._send_json({"ok": True, "data": STATE.service.get_character_detail_payload(char_id)})
            if parsed.path == "/api/equipment":
                return self._api_search_equipment(parse_qs(parsed.query))
            if parsed.path.startswith("/api/equipment/"):
                equipment_id = parsed.path.rsplit("/", 1)[-1]
                return self._send_json({"ok": True, "data": STATE.service.get_equipment(equipment_id)})
            if parsed.path == "/api/buff-subids":
                params = parse_qs(parsed.query)
                buff_id = (params.get("buff_id") or [""])[0]
                return self._send_json({"ok": True, "data": STATE.service.list_buff_subid_options(buff_id)})
            if parsed.path == "/api/equipment-buff-subids":
                params = parse_qs(parsed.query)
                buff_id = (params.get("buff_id") or [""])[0]
                return self._send_json({"ok": True, "data": STATE.service.list_equipment_buff_subid_options(buff_id)})
            if parsed.path == "/api/effect-format":
                params = parse_qs(parsed.query)
                effect = [
                    _to_int((params.get("buff_id") or ["0"])[0]),
                    _to_int((params.get("sub_id") or ["0"])[0]),
                    _to_int((params.get("target") or ["1"])[0], 1),
                    _to_int((params.get("duration") or ["0"])[0]),
                    _to_float((params.get("value") or ["0"])[0]),
                ]
                return self._send_json({"ok": True, "data": {"text": STATE.service.format_runtime_effect_list([effect])[0]}})
            if parsed.path == "/api/recommended":
                return self._api_recommended(parse_qs(parsed.query))
            if parsed.path == "/api/character-presets":
                return self._send_json({"ok": True, "data": _load_character_presets()})
            if parsed.path == "/api/arena-presets":
                return self._send_json({"ok": True, "data": _load_arena_presets()})
            if parsed.path == "/api/arena-enemy-data":
                return self._api_arena_enemy_data()
            if parsed.path == "/api/vs-presets":
                return self._api_vs_presets()
            if parsed.path.startswith("/assets/"):
                return self._send_asset(parsed.path)
            if parsed.path == "/" or not parsed.path.startswith("/api/"):
                return self._send_static(parsed.path)
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._send_error_json(exc)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = _read_json_body(self)
            if parsed.path == "/api/calculate":
                return self._api_calculate(payload)
            if parsed.path == "/api/batch-summary":
                return self._api_batch_summary(payload)
            if parsed.path == "/api/weekly-arena-solve":
                return self._api_weekly_arena_solve(payload)
            if parsed.path == "/api/vs-manual-solve":
                return self._api_vs_manual_solve(payload)
            if parsed.path == "/api/character-presets":
                return self._api_save_character_presets(payload)
            if parsed.path == "/api/arena-presets":
                return self._api_save_arena_presets(payload)
            if parsed.path.startswith("/api/characters/") and parsed.path.endswith("/save"):
                char_id = _to_int(parsed.path.split("/")[-2])
                STATE.service.save_character_full(char_id, payload)
                return self._send_json({"ok": True})
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._send_error_json(exc)

    def _api_arena_enemy_data(self) -> None:
        source = find_arena_xlsx(BASE_DIR)
        if not source:
            return self._send_json(
                {
                    "ok": True,
                    "data": {
                        "source": "",
                        "csv_path": str(ARENA_DATA_CSV_PATH),
                        "json_path": str(ARENA_DATA_JSON_PATH),
                        "rows": [],
                        "row_count": 0,
                    },
                }
            )
        payload = ensure_arena_enemy_data(source, ARENA_DATA_CSV_PATH, ARENA_DATA_JSON_PATH)
        data = dict(payload)
        data["csv_path"] = str(ARENA_DATA_CSV_PATH)
        data["json_path"] = str(ARENA_DATA_JSON_PATH)
        data["row_count"] = len(payload.get("rows", []))
        return self._send_json({"ok": True, "data": data})

    def _api_bootstrap(self) -> None:
        service = STATE.service
        STATE.character_index.load()
        equipment_options = service.list_equipment_options()
        self._send_json(
            {
                "ok": True,
                "data": {
                    "version": "v1.2",
                    "root_dir": ROOT_DIR,
                    "quality_labels": QUALITY_LABELS,
                    "quality_state_text": QUALITY_STATE_TEXT,
                    "quality_default": QUALITY_DEFAULT,
                    "type_labels": TYPE_LABELS,
                    "element_labels": ELEMENT_RAW_LABELS,
                    "bullet_labels": BULLET_RAW_LABELS,
                    "buff_id_options": service.list_buff_id_options(),
                    "equipment_buff_id_options": service.list_equipment_buff_id_options(),
                    "equipment_options": equipment_options,
                    "world_group_options": service.get_world_group_options(),
                    "tribe_options": service.get_tribe_options(),
                    "character_options": STATE.character_options("", limit=5000),
                    "defaults": {
                        "enemy_id": DEFAULT_ENEMY_ID,
                        "ally_id": DEFAULT_ALLY_ID,
                        "attack_type": DEFAULT_ATTACK_TYPE,
                        "spirit_level": DEFAULT_SPIRIT_LEVEL,
                        "target_enemy_pos": DEFAULT_TARGET_ENEMY_POS,
                        "shield_open_count": DEFAULT_SHIELD_OPEN_COUNT,
                    },
                },
            }
        )

    def _api_search_characters(self, params: Dict[str, List[str]]) -> None:
        data = STATE.service.search_characters(
            type_values=_split_values((params.get("types") or [""])[0]),
            element_values=_split_values((params.get("elements") or [""])[0]),
            bullet_values=_split_values((params.get("bullets") or [""])[0]),
            killer_tribes=_split_values((params.get("killers") or [""])[0]),
            world_groups=_split_values((params.get("world_groups") or [""])[0]),
            re_only=(params.get("re_only") or [""])[0],
            name_query=(params.get("name") or [""])[0],
            element_logic=(params.get("element_logic") or ["any"])[0],
            bullet_logic=(params.get("bullet_logic") or ["any"])[0],
            killer_logic=(params.get("killer_logic") or ["any"])[0],
        )
        self._send_json({"ok": True, "data": data})

    def _api_search_equipment(self, params: Dict[str, List[str]]) -> None:
        buff_filters: List[Dict[str, Any]] = []
        for idx in range(1, 4):
            buff_id = (params.get(f"buff_id_{idx}") or params.get("buff_id") or [""])[0]
            sub_ids = _split_values((params.get(f"sub_ids_{idx}") or params.get("sub_ids") or [""])[0])
            value = (params.get(f"value_{idx}") or params.get("value") or [""])[0]
            target = (params.get(f"target_{idx}") or params.get("target") or [""])[0]
            type_conditions = _split_values((params.get(f"type_conditions_{idx}") or params.get("type_conditions") or [""])[0])
            if buff_id or sub_ids or value or target or type_conditions:
                buff_filters.append(
                    {
                        "buff_id": buff_id,
                        "sub_ids": sub_ids,
                        "value": value,
                        "target_type": target,
                        "type_conditions": type_conditions,
                    }
                )
        data = STATE.service.search_equipment(
            query=(params.get("q") or [""])[0],
            stars=_split_values((params.get("stars") or [""])[0]),
            style_code=_split_values((params.get("style_code") or [""])[0]),
            buff_filters=buff_filters,
            buff_filter_logic=(params.get("buff_logic") or ["and"])[0],
            stat_filters=_split_values((params.get("stats") or [""])[0]),
        )
        self._send_json({"ok": True, "data": data})

    def _api_recommended(self, params: Dict[str, List[str]]) -> None:
        char_id = _to_int((params.get("character_id") or [""])[0])
        result = {
            key: STATE.service.get_recommended_equipment_id(char_id, key)
            for key in ("1a", "2a", "1b", "2b", "5")
        }
        self._send_json({"ok": True, "data": result})

    def _api_calculate(self, payload: Dict[str, Any]) -> None:
        enemy_slots, ally_slots, process_config = _configs_from_payload(payload)
        result = STATE.service.run_single(
            enemy_slots,
            ally_slots,
            process_config=process_config,
            character_presets=_extract_character_presets(payload),
        )
        self._send_json({"ok": True, "data": result})

    def _api_batch_summary(self, payload: Dict[str, Any]) -> None:
        enemy_slots, ally_slots, process_config = _configs_from_payload(payload)
        template_pos = _to_int(payload.get("template_ally_pos"), 0)
        ally_template = ally_slots.get(template_pos) or ally_slots[0]
        rows = STATE.service.run_batch_single_template(
            enemy_slots,
            ally_template,
            process_config=process_config,
            character_presets=_extract_character_presets(payload),
            equipment_policy=str(payload.get("equipment_policy", "default") or "default"),
        )
        csv_path = _write_summary_csv(rows)
        self._send_json({"ok": True, "data": {"csv_path": csv_path, "rows": rows[:200], "row_count": len(rows)}})

    def _api_weekly_arena_solve(self, payload: Dict[str, Any]) -> None:
        character_presets = _extract_character_presets(payload)
        candidate_ids = [
            _to_int(char_id)
            for char_id, preset in character_presets.items()
            if _to_int(char_id) > 0 and not bool((preset or {}).get("unowned", False))
        ]
        for arena in payload.get("weekly_arenas") or []:
            for wave in (arena or {}).values():
                if not isinstance(wave, dict):
                    continue
                for value in str(wave.get("role_ids", "") or "").replace("，", ",").split(","):
                    if _to_int(value) > 0:
                        candidate_ids.append(_to_int(value))
        candidate_ids = sorted(set(candidate_ids))
        if not candidate_ids:
            candidate_ids = STATE.service.discover_all_ids()

        base_payload = dict(payload)
        base_payload["mode"] = "arena"
        waves_raw = payload.get("enemy_waves") or {}
        arenas_raw = payload.get("weekly_arenas") or [waves_raw, waves_raw, waves_raw, waves_raw]
        arena_meta_raw = payload.get("weekly_arena_meta") or []
        process_payload = payload.get("process") or {}
        process_config = ProcessConfig.from_payload(process_payload)
        default_type_boosts = set(_to_int(v) for v in process_config.field_buffs.arena_type_boosts or [])

        arenas: List[Dict[str, Any]] = []
        flat_tasks: List[Dict[str, Any]] = []
        for arena_idx, arena_waves in enumerate(arenas_raw[:4], start=1):
            arena_result = {"arena": arena_idx, "waves": []}
            arena_meta = arena_meta_raw[arena_idx - 1] if isinstance(arena_meta_raw, list) and len(arena_meta_raw) >= arena_idx else {}
            type_boosts = set(_to_int(v) for v in ((arena_meta or {}).get("types") or [])) or set(default_type_boosts)
            only_boosted = bool((arena_meta or {}).get("only_boosted", True))
            process_config.field_buffs.arena_yinyang = str((arena_meta or {}).get("yinyang") or ("yang" if arena_idx % 2 == 1 else "yin"))
            for wave_idx in range(1, 4):
                wave_payload = (arena_waves or {}).get(str(wave_idx)) or (arena_waves or {}).get(wave_idx) or {}
                enemy_slots = {
                    pos: _enemy_config_from_payload((wave_payload or {}).get(str(pos)) or (wave_payload or {}).get(pos) or {})
                    for pos in range(3)
                }
                enabled_enemy_count = sum(1 for cfg in enemy_slots.values() if cfg.enabled)
                fixed_hp = ARENA_FIXED_LUNATIC_HP.get(max(1, min(3, enabled_enemy_count)), {}).get(wave_idx, 0)
                if fixed_hp > 0:
                    for cfg in enemy_slots.values():
                        if cfg.enabled:
                            cfg.hp = fixed_hp
                manual_ids = [
                    _to_int(value)
                    for value in str((wave_payload or {}).get("role_ids", "") or "").replace("，", ",").split(",")
                    if _to_int(value) > 0
                ]
                wave_candidate_ids = sorted(set(manual_ids)) if manual_ids else candidate_ids
                enemy_hp_total = sum(cfg.hp for cfg in enemy_slots.values() if cfg.enabled)
                wave_candidates: List[Dict[str, Any]] = []
                if enemy_hp_total <= 0:
                    arena_result["waves"].append({"wave": wave_idx, "enemy_hp_total": 0, "candidates": []})
                    continue
                for char_id in wave_candidate_ids:
                    meta = STATE.service.load_character_meta(char_id)
                    type_value = _to_int(meta.get("type", 0))
                    if only_boosted and type_boosts and type_value not in type_boosts:
                        continue
                    equipment_ids = STATE.service.fill_missing_recommended_equipment_ids(char_id, {})
                    ally_slots = {
                        0: AllySlotConfig(
                            enabled=True,
                            character_id=char_id,
                            initial_spirit=1.0,
                            barrier_count=5,
                            skill_order_text="0,1,2",
                            shield_open_count=0,
                            attack_type="5",
                            spirit_level=3,
                            target_enemy_pos=0,
                            equipment_ids=equipment_ids,
                        ),
                        1: AllySlotConfig(enabled=False),
                        2: AllySlotConfig(enabled=False),
                    }
                    try:
                        result = STATE.service.run_single(
                            enemy_slots,
                            ally_slots,
                            process_config=process_config,
                            character_presets=character_presets,
                        )
                        total = int(result.get("total_damage", 0) or 0)
                        yang_total = int(result.get("yang_damage_total", 0) or 0)
                        yin_total = int(result.get("yin_damage_total", 0) or 0)
                        row = {
                            "arena": arena_idx,
                            "wave": wave_idx,
                            "character_id": char_id,
                            "name": STATE.service.translate_character_name(meta.get("name", ""), char_id),
                            "world_group": meta.get("world_group", ""),
                            "type": type_value,
                            "type_label": meta.get("type_label", ""),
                            "damage": total,
                            "yang_damage": yang_total,
                            "yin_damage": yin_total,
                            "yang_ratio": round(yang_total / total * 100.0, 2) if total > 0 else 0.0,
                            "yin_ratio": round(yin_total / total * 100.0, 2) if total > 0 else 0.0,
                            "enemy_hp_total": enemy_hp_total,
                            "overflow": total - enemy_hp_total,
                            "deficit": max(0, enemy_hp_total - total),
                            "clear": total >= enemy_hp_total,
                            "type_boosted": type_value in type_boosts,
                        }
                        wave_candidates.append(row)
                    except Exception:
                        continue
                answer_candidates = [row for row in wave_candidates if int(row.get("overflow", -10**18)) > -1000]
                clear_candidates = [row for row in answer_candidates if row.get("clear")]
                miss_candidates = [row for row in answer_candidates if not row.get("clear")]
                clear_candidates.sort(key=lambda row: (0 if row["type_boosted"] else 1, row["overflow"], row["damage"]))
                miss_candidates.sort(key=lambda row: (0 if row["type_boosted"] else 1, row["deficit"], -row["damage"]))
                display_candidates = sorted(answer_candidates, key=lambda row: (0 if row["clear"] else 1, row["overflow"], row["damage"], row["character_id"]))
                arena_result["waves"].append({"wave": wave_idx, "enemy_hp_total": enemy_hp_total, "candidates": display_candidates, "raw_candidate_count": len(wave_candidates)})
                flat_tasks.append({"arena": arena_idx, "wave": wave_idx, "candidates": clear_candidates or miss_candidates})
            arenas.append(arena_result)

        used = set()
        recommended: List[Dict[str, Any]] = []
        for task in sorted(flat_tasks, key=lambda item: len(item["candidates"])):
            pick = next((row for row in task["candidates"] if row["character_id"] not in used), None)
            if pick:
                used.add(pick["character_id"])
                recommended.append(pick)
            else:
                recommended.append({"arena": task["arena"], "wave": task["wave"], "status": "无不重复可用角色"})
        self._send_json({"ok": True, "data": {"arenas": arenas, "recommended": recommended}})

    def _api_vs_manual_solve(self, payload: Dict[str, Any]) -> None:
        enemy_slots, ally_slots, process_config = _configs_from_payload(payload)
        manual_turn = max(1, _to_int((payload.get("manual_state") or {}).get("turn"), 1))
        result = STATE.service.run_single(
            enemy_slots,
            ally_slots,
            process_config=process_config,
            character_presets=_extract_character_presets(payload),
        )
        enemy_totals = result.get("enemy_totals") or {}
        ally_totals = result.get("ally_totals") or {}
        selected_equipment = result.get("selected_equipment") or {}
        def _buff_text(rows: Any) -> List[str]:
            texts: List[str] = []
            for row in rows or []:
                if not isinstance(row, (list, tuple)) or len(row) < 4:
                    continue
                try:
                    texts.append(
                        STATE.service._format_effect_text(row[0], row[1], 1, row[2], row[3], context="skill")
                    )
                except Exception:
                    texts.append(",".join(str(v) for v in row))
            return texts

        ally_states: List[Dict[str, Any]] = []
        for pos, cfg in ally_slots.items():
            if not cfg.enabled:
                continue
            meta = STATE.service.load_character_meta(cfg.character_id)
            equipment = selected_equipment.get(pos, selected_equipment.get(str(pos), {})) or {}
            ally_states.append(
                {
                    "side": "ally",
                    "pos": pos,
                    "character_id": cfg.character_id,
                    "name": STATE.service.translate_character_name(meta.get("name", ""), cfg.character_id),
                    "damage": _to_int(ally_totals.get(str(pos), ally_totals.get(pos, 0)), 0),
                    "barrier_count": cfg.barrier_count,
                    "attack_type": cfg.attack_type,
                    "spirit_level": cfg.spirit_level,
                    "shield_open_count": cfg.shield_open_count,
                    "equipment_name": equipment.get("name", ""),
                    "buffs": cfg.buffs,
                    "buffs_text": _buff_text(cfg.buffs),
                    "speed": _to_int(meta.get("speed", 0), 0),
                }
            )
        ally_state_by_pos = {int(row["pos"]): row for row in ally_states}
        actual_order_positions = [
            _to_int(pos, -1)
            for pos in (result.get("attack_order") or [])
            if _to_int(pos, -1) in ally_state_by_pos
        ]
        if not actual_order_positions:
            actual_order_positions = [
                row["pos"]
                for row in sorted(ally_states, key=lambda row: (-_to_int(row.get("speed", 0), 0), row["pos"]))
            ]
        attack_order = [
            {
                "pos": pos,
                "character_id": ally_state_by_pos[pos]["character_id"],
                "name": ally_state_by_pos[pos]["name"],
                "speed": _to_int(ally_state_by_pos[pos].get("speed", 0), 0),
            }
            for pos in actual_order_positions
        ]
        enemy_states: List[Dict[str, Any]] = []
        for pos, cfg in enemy_slots.items():
            if not cfg.enabled:
                continue
            damage = _to_int(enemy_totals.get(str(pos), enemy_totals.get(pos, 0)), 0)
            hp = _to_int(cfg.hp, 0)
            meta = STATE.service.load_character_meta(cfg.character_id)
            enemy_states.append(
                {
                    "side": "enemy",
                    "pos": pos,
                    "character_id": cfg.character_id,
                    "name": STATE.service.translate_character_name(meta.get("name", ""), cfg.character_id),
                    "hp": hp,
                    "damage": damage,
                    "remaining_hp": max(0, hp - damage),
                    "barrier_count": cfg.barrier_count,
                    "quality": cfg.quality,
                    "buffs": cfg.buffs,
                    "buffs_text": _buff_text(cfg.buffs),
                    "enemy_skill_effects_text": STATE.service.format_runtime_effect_list(cfg.enemy_skill_effects or []),
                }
            )
        hp_tracker = {int(row["pos"]): int(row["hp"]) for row in enemy_states}
        attack_steps: List[Dict[str, Any]] = []
        details = result.get("details") or []
        for attacker_pos in actual_order_positions:
            attacker = ally_state_by_pos.get(attacker_pos) or {}
            damage_by_enemy: Dict[int, int] = {}
            for detail in details:
                if _to_int(detail.get("attacker_pos"), -1) != attacker_pos:
                    continue
                enemy_pos = _to_int(detail.get("enemy_pos"), -1)
                if enemy_pos < 0:
                    continue
                damage_by_enemy[enemy_pos] = damage_by_enemy.get(enemy_pos, 0) + _to_int(detail.get("damage_int"), 0)
            for enemy_pos, damage in damage_by_enemy.items():
                before = hp_tracker.get(enemy_pos, 0)
                after = max(0, before - damage)
                hp_tracker[enemy_pos] = after
                attack_steps.append(
                    {
                        "attacker_pos": attacker_pos,
                        "attacker_name": attacker.get("name", f"我方{attacker_pos}"),
                        "enemy_pos": enemy_pos,
                        "damage": damage,
                        "remaining_hp": after,
                    }
                )
        data = {
            "turn": manual_turn,
            "total_damage": result.get("total_damage", 0),
            "yang_damage_total": result.get("yang_damage_total", 0),
            "yin_damage_total": result.get("yin_damage_total", 0),
            "ally_states": ally_states,
            "attack_order": attack_order,
            "enemy_states": enemy_states,
            "attack_steps": attack_steps,
            "state": {
                "turn": manual_turn,
                "ally_states": ally_states,
                "enemy_states": enemy_states,
            },
            "raw_result": result,
        }
        self._send_json({"ok": True, "data": data})

    def _api_save_character_presets(self, payload: Dict[str, Any]) -> None:
        presets = payload.get("character_presets")
        if not isinstance(presets, dict):
            presets = payload if isinstance(payload, dict) else {}
        _save_character_presets(presets)
        self._send_json({"ok": True, "data": {"path": str(CHARACTER_PRESET_DIR)}})

    def _api_save_arena_presets(self, payload: Dict[str, Any]) -> None:
        presets = payload.get("arena_presets")
        if not isinstance(presets, dict):
            presets = payload if isinstance(payload, dict) else {}
        normalized = {str(k): _normalize_arena_preset(k, v) for k, v in (presets or {}).items() if isinstance(v, dict)}
        _save_json_file(ARENA_PRESET_PATH, normalized)
        _sync_arena_data_from_presets(normalized)
        self._send_json({"ok": True, "data": {"path": str(ARENA_PRESET_PATH)}})

    def _api_vs_presets(self) -> None:
        source = next((path for path in VS_LUA_SOURCE_CANDIDATES if path.exists()), VS_LUA_SOURCE_CANDIDATES[0])
        if not source.exists():
            return self._send_json({"ok": True, "data": {"source": str(source), "row_count": 0, "rows": [], "presets": []}})
        payload = ensure_vs_json(source, VS_JSON_PATH)
        presets = [_enrich_vs_preset(row) for row in payload.get("presets", [])[:1000]]
        preview = {
            "source": payload.get("source", str(source)),
            "json_path": str(VS_JSON_PATH),
            "row_count": len(payload.get("presets", [])),
            "td_count": payload.get("td_count", 0),
            "st_count": payload.get("st_count", 0),
            "card_count": payload.get("card_count", 0),
            "vs_effect_count": payload.get("vs_effect_count", 0),
            "vs_group_count": payload.get("vs_group_count", 0),
            "rows": presets,
            "presets": presets,
        }
        self._send_json({"ok": True, "data": preview})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="lwMAA v1.2 desktop app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--browser-mode", choices=("app", "tab", "none"), default="app", help="app=无地址栏软件窗口，tab=普通浏览器标签，none=只启动后端")
    parser.add_argument("--no-browser", action="store_true", help="兼容旧参数，等同于 --browser-mode none")
    return parser.parse_args()


def _candidate_browser_paths() -> List[str]:
    names = ["msedge.exe", "chrome.exe"]
    paths: List[str] = []
    for name in names:
        found = shutil.which(name)
        if found:
            paths.append(found)

    local_app = os.environ.get("LOCALAPPDATA", "")
    program_files = [os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", "")]
    fixed_candidates = [
        Path(program_files[0]) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(program_files[1]) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(local_app) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(program_files[0]) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(program_files[1]) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(local_app) / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]
    for path in fixed_candidates:
        if path and path.exists():
            paths.append(str(path))

    deduped: List[str] = []
    seen = set()
    for path in paths:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def _launch_desktop_window(url: str) -> Optional[subprocess.Popen]:
    profile_dir = APP_DIR / ".browser_profile"
    profile_dir.mkdir(exist_ok=True)
    for browser in _candidate_browser_paths():
        try:
            return subprocess.Popen(
                [
                    browser,
                    f"--app={url}",
                    f"--user-data-dir={profile_dir}",
                    "--no-first-run",
                    "--disable-features=Translate",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            continue
    return None


def main() -> None:
    args = parse_args()
    _ensure_runtime_dirs()
    if args.no_browser:
        args.browser_mode = "none"
    httpd = ThreadingHTTPServer((args.host, args.port), RequestHandler)
    url = f"http://{args.host}:{args.port}/"
    _log(f"lwMAA v1.2 running: {url}, browser_mode={args.browser_mode}")
    print(f"lwMAA v1.2 running: {url}")

    if args.browser_mode == "none":
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("server stopped")
        finally:
            httpd.server_close()
        return

    if args.browser_mode == "tab":
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("server stopped")
        finally:
            httpd.server_close()
        return

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.3)
    app_process = _launch_desktop_window(url)
    if app_process is None:
        webbrowser.open(url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
    else:
        try:
            app_process.wait()
        except KeyboardInterrupt:
            pass
    httpd.shutdown()
    httpd.server_close()


if __name__ == "__main__":
    main()
