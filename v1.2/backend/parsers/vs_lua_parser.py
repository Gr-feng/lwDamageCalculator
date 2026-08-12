from __future__ import annotations

import json
import csv
import re
from pathlib import Path
from typing import Any, Dict, List


TD_FIELD_NAMES = [
    "td_id",
    "enemy_id",
    "display_name",
    "name",
    "lv60_hp",
    "lv60_yang_atk",
    "lv60_yang_def",
    "lv60_yin_atk",
    "lv60_yin_def",
    "lv60_speed",
    "lv100_hp",
    "lv100_yang_atk",
    "lv100_yang_def",
    "lv100_yin_atk",
    "lv100_yin_def",
    "lv100_speed",
    "unknown_1",
    "spell_gauge",
    "barrier_count",
]

ST_FIELD_NAMES = [
    "vs_id",
    "title",
    "enemy_td_0",
    "enemy_td_1",
    "enemy_td_2",
    "effect_group_id",
    "asset_key",
    "test_flag",
    "drop_type",
    "card_id",
    "main_character_id",
    "tag_group_base_id",
    "start_at",
    "end_at",
    "category",
    "enabled",
]

VS_EFFECT_FIELD_NAMES = ["effect_id", "name", "description", "side", "kind", "sub_id", "value"]
VS_GROUP_FIELD_NAMES = ["group_id", "tag", "effect_id_1", "effect_id_2"]
CARD_FIELD_NAMES = ["card_id", "name"]

ELEMENT_LABEL_TO_INDEX = {"日": 0, "月": 1, "火": 2, "水": 3, "木": 4, "金": 5, "土": 6, "星": 7, "无": 8}
STATS_KEYS = ("hp", "yang_atk", "yang_def", "yin_atk", "yin_def", "speed")
STAT_EFFECT_LABELS = {1: "最大体力", 2: "阳攻", 3: "阳防", 4: "阴攻", 5: "阴防", 6: "速度", 7: "命中", 8: "回避"}
BULLET_EFFECT_LABELS = {1: "通常弹", 3: "镭射弹", 4: "体术弹", 5: "斩击弹", 6: "动能弹", 7: "流体弹", 8: "能量弹", 9: "御符弹", 10: "光弹", 11: "尖弹", 12: "追踪弹"}
TYPE_EFFECT_LABELS = {1: "防御式", 2: "支援式", 3: "回复式", 4: "干扰式", 5: "攻击式", 6: "技巧式", 7: "速攻式", 8: "破坏式"}


def _load_tribe_reverse_map(source_path: Path) -> Dict[str, int]:
    project_dir = Path(__file__).resolve().parents[2]
    candidates = [
        source_path.parent / "v1.2" / "tribe_extracted.csv",
        source_path.parent / "v1.2" / "data_tables" / "tribe_extracted.csv",
        source_path.parent / "tribe_extracted.csv",
        project_dir / "data_tables" / "tribe_extracted.csv",
        project_dir / "tribe_extracted.csv",
    ]
    for path in candidates:
        if not path.exists():
            continue
        out: Dict[str, int] = {}
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    name = str(row.get("tribe_name", "") or "").strip()
                    tribe_id = int(str(row.get("ID", "") or "0").strip())
                    if name and tribe_id > 0:
                        out[name] = tribe_id
            if out:
                return out
        except Exception:
            continue
    return {}


def _split_top_level(text: str) -> List[str]:
    items: List[str] = []
    buf: List[str] = []
    depth = 0
    in_string = False
    escape = False
    for ch in text:
        if in_string:
            buf.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            buf.append(ch)
            continue
        if ch == "{":
            depth += 1
            buf.append(ch)
            continue
        if ch == "}":
            depth -= 1
            buf.append(ch)
            continue
        if ch == "," and depth == 0:
            items.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf:
        items.append("".join(buf).strip())
    return items


def _table_rows(lua_text: str, table_name: str) -> List[str]:
    marker = f"{table_name}="
    body_start = lua_text.find(marker)
    if body_start < 0:
        return []
    start = lua_text.find("{", body_start + len(marker))
    if start < 0:
        return []
    rows: List[str] = []
    depth = 0
    row_start = -1
    in_string = False
    escape = False
    for pos in range(start, len(lua_text)):
        ch = lua_text[pos]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
            if depth == 2:
                row_start = pos
            continue
        if ch == "}":
            if depth == 2 and row_start >= 0:
                rows.append(lua_text[row_start + 1 : pos])
                row_start = -1
            depth -= 1
            if depth <= 0 and pos > start:
                break
    return rows


def _parse_value(text: str) -> Any:
    text = text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1].replace('\\"', '"').replace("\\n", "\n")
    if len(text) >= 2 and text[0] == "{" and text[-1] == "}":
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_parse_value(part) for part in _split_top_level(inner)]
    if text == "":
        return ""
    try:
        if "." in text:
            return float(text)
        return int(text)
    except Exception:
        return text


def _parse_row(raw_row: str, names: List[str]) -> Dict[str, Any]:
    fields = _split_top_level(raw_row)
    parsed: Dict[str, Any] = {
        "raw_field_count": len(fields),
        "raw": raw_row,
        "fields": [_parse_value(field) for field in fields],
    }
    for idx, name in enumerate(names):
        if idx < len(fields):
            parsed[name] = _parse_value(fields[idx])
    return parsed


def _effect_description_from_fields(row: Dict[str, Any]) -> str:
    try:
        side = int(row.get("side", 0) or 0)
        kind = int(row.get("kind", 0) or 0)
        sub_id = int(row.get("sub_id", 0) or 0)
        value = float(row.get("value", 0) or 0)
    except Exception:
        return ""
    side_label = {2: "己方全体", 4: "敌方全体"}.get(side, f"side{side}")
    sign_text = "上升" if value >= 0 else "下降"
    abs_value = abs(value)
    if kind == 1:
        label = STAT_EFFECT_LABELS.get(sub_id, f"能力{sub_id}")
        return f"{side_label}{label}{sign_text}{abs_value:g}% (永久)"
    if kind == 10:
        label = BULLET_EFFECT_LABELS.get(sub_id, f"弹种{sub_id}")
        return f"{side_label}{label}的伤害{sign_text}{abs_value:g}% (永久)"
    if kind == 4:
        label = TYPE_EFFECT_LABELS.get(sub_id, f"Type{sub_id}")
        return f"{side_label}{label}综合强度{sign_text}{abs_value:g}% (永久)"
    if kind == 2:
        return f"{side_label}对种族特攻受伤倍率轻减{sign_text}{abs_value:g}% (永久)"
    return f"{side_label}效果 kind={kind} subID={sub_id} value={value:g}"


def _normalize_vs_effect(row: Dict[str, Any]) -> Dict[str, Any]:
    if not str(row.get("description", "") or "").strip():
        row["description"] = _effect_description_from_fields(row)
    if not str(row.get("name", "") or "").strip():
        desc = str(row.get("description", "") or "")
        row["name"] = desc.split(" (", 1)[0] if desc else f"effect {row.get('effect_id', '')}"
    return row


def _stats(row: Dict[str, Any], prefix: str) -> Dict[str, Any]:
    return {
        "hp": row.get(f"{prefix}_hp", 0),
        "yang_atk": row.get(f"{prefix}_yang_atk", 0),
        "yang_def": row.get(f"{prefix}_yang_def", 0),
        "yin_atk": row.get(f"{prefix}_yin_atk", 0),
        "yin_def": row.get(f"{prefix}_yin_def", 0),
        "speed": row.get(f"{prefix}_speed", 0),
    }


def interpolate_stats(row: Dict[str, Any], level: int) -> Dict[str, int]:
    level = max(60, min(100, int(level)))
    lv60 = row.get("lv60_stats") or _stats(row, "lv60")
    lv100 = row.get("lv100_stats") or _stats(row, "lv100")
    ratio = (level - 60) / 40.0
    return {
        key: int(round(float(lv60.get(key, 0) or 0) + (float(lv100.get(key, 0) or 0) - float(lv60.get(key, 0) or 0)) * ratio))
        for key in STATS_KEYS
    }


def _quality_from_text(weak_text: Any, resist_text: Any) -> List[int]:
    quality = [1] * 9
    for ch in str(weak_text or ""):
        idx = ELEMENT_LABEL_TO_INDEX.get(ch)
        if idx is not None:
            quality[idx] = 0
    for ch in str(resist_text or ""):
        idx = ELEMENT_LABEL_TO_INDEX.get(ch)
        if idx is not None:
            quality[idx] = 2
    return quality


def _is_effect_list(value: Any) -> bool:
    if not isinstance(value, list) or len(value) < 1:
        return False
    return all(isinstance(item, list) and len(item) >= 5 for item in value)


def _is_phase_ids(value: Any, current_td_id: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) >= 1
        and all(isinstance(item, int) for item in value)
        and int(current_td_id) in [int(item) for item in value]
    )


def _looks_like_tribes_text(value: Any) -> bool:
    text = str(value or "")
    if not text or "," not in text:
        return False
    return not any(mark in text for mark in ("<color", "\n", "上升", "下降", "伤害"))


def _strip_color_tags(text: Any) -> str:
    return re.sub(r"</?color(?:=[^>]+)?>", "", str(text or "")).strip()


def _tribe_ids_from_text(text: Any, reverse_map: Dict[str, int]) -> List[int]:
    ids: List[int] = []
    seen = set()
    for part in str(text or "").replace("，", ",").split(","):
        name = part.strip()
        if not name:
            continue
        tribe_id = reverse_map.get(name, 0)
        if tribe_id <= 0 or tribe_id in seen:
            continue
        seen.add(tribe_id)
        ids.append(tribe_id)
    return ids


def _parse_td(raw_row: str, tribe_reverse_map: Dict[str, int] | None = None) -> Dict[str, Any]:
    row = _parse_row(raw_row, TD_FIELD_NAMES)
    row["lv60_stats"] = _stats(row, "lv60")
    row["lv100_stats"] = _stats(row, "lv100")
    fields = row.get("fields", [])
    td_id = int(row.get("td_id", 0) or 0)
    row["card_buffs"] = fields[23:26] if len(fields) >= 26 else []
    row["weak_elements_text"] = fields[26] if len(fields) > 26 else ""
    row["resist_elements_text"] = fields[27] if len(fields) > 27 else ""
    row["quality_code"] = fields[28] if len(fields) > 28 else ""
    row["quality"] = _quality_from_text(row["weak_elements_text"], row["resist_elements_text"])

    row["phase_ids"] = []
    row["ex1_name"] = ""
    row["ex1_buffs"] = []
    row["ex2_name"] = ""
    row["ex2_buffs"] = []
    row["skill_name"] = ""
    row["skill_buffs"] = []

    cursor = 29
    if len(fields) > cursor and isinstance(fields[cursor], int):
        row["unknown_after_quality"] = fields[cursor]
        cursor += 1
    if len(fields) > cursor and fields[cursor] == "":
        cursor += 1
    if len(fields) > cursor and fields[cursor] == "":
        cursor += 1

    pre_phase_pairs: List[tuple[str, list]] = []
    while cursor + 1 < len(fields) and isinstance(fields[cursor], str) and _is_effect_list(fields[cursor + 1]):
        pre_phase_pairs.append((fields[cursor], fields[cursor + 1]))
        cursor += 2

    if len(fields) > cursor and _is_phase_ids(fields[cursor], td_id):
        row["phase_ids"] = [int(item) for item in fields[cursor]]
        cursor += 1

    if row["phase_ids"]:
        if len(pre_phase_pairs) >= 1:
            row["ex1_name"], row["ex1_buffs"] = pre_phase_pairs[0]
        if len(pre_phase_pairs) >= 2:
            row["ex2_name"], row["ex2_buffs"] = pre_phase_pairs[1]
        if cursor + 1 < len(fields) and isinstance(fields[cursor], str) and _is_effect_list(fields[cursor + 1]):
            row["skill_name"], row["skill_buffs"] = fields[cursor], fields[cursor + 1]
            cursor += 2
    elif pre_phase_pairs:
        row["skill_name"], row["skill_buffs"] = pre_phase_pairs[-1]
        if len(pre_phase_pairs) >= 2:
            row["ex1_name"], row["ex1_buffs"] = pre_phase_pairs[0]
            row["ex2_name"], row["ex2_buffs"] = pre_phase_pairs[1]

    while cursor < len(fields) and fields[cursor] == "":
        cursor += 1
    row["tribes_text"] = ""
    for idx in range(cursor, len(fields)):
        if _looks_like_tribes_text(fields[idx]):
            row["tribes_text"] = fields[idx]
            cursor = idx + 1
            break

    row["attack_phase_payloads"] = []
    for idx in range(cursor, len(fields)):
        value = fields[idx]
        if isinstance(value, list) and len(value) >= 5 and isinstance(value[0], list):
            row["attack_phase_payloads"].append(value)

    row["extra_description"] = _strip_color_tags(fields[-1]) if fields and isinstance(fields[-1], str) else ""
    row["tribe_ids"] = _tribe_ids_from_text(row["tribes_text"], tribe_reverse_map or {})
    row["level_100_config"] = {
        "character_id": row.get("enemy_id", 0),
        "hp": row["lv100_stats"]["hp"],
        "yang_atk": row["lv100_stats"]["yang_atk"],
        "yang_def": row["lv100_stats"]["yang_def"],
        "yin_atk": row["lv100_stats"]["yin_atk"],
        "yin_def": row["lv100_stats"]["yin_def"],
        "speed": row["lv100_stats"]["speed"],
        "barrier_count": row.get("barrier_count", 5),
        "quality": row["quality"],
        "tribe_text": ",".join(str(v) for v in row.get("tribe_ids", [])) or row.get("tribes_text", ""),
        "enemy_skill_effects": row.get("skill_buffs", []),
    }
    return row


def _parse_table(lua_text: str, table_name: str, names: List[str]) -> List[Dict[str, Any]]:
    return [_parse_row(raw, names) for raw in _table_rows(lua_text, table_name)]


def _effect_key(row: Dict[str, Any]) -> tuple[int, int, float]:
    return (
        int(row.get("kind", 0) or 0),
        int(row.get("sub_id", 0) or 0),
        float(row.get("value", 0) or 0),
    )


def _compact_effect(row: Dict[str, Any]) -> Dict[str, Any]:
    kind, sub_id, value = _effect_key(row)
    value_out: int | float = int(value) if abs(value - int(value)) <= 1e-9 else value
    return {"kind": kind, "sub_id": sub_id, "value": value_out}


def _effect_translation_rows(effect_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[tuple[int, int, float]] = set()
    rows: List[Dict[str, Any]] = []
    for row in effect_rows:
        key = _effect_key(row)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            **_compact_effect(row),
            "name": row.get("name", ""),
            "description": row.get("description", ""),
        })
    return rows


def _st_to_preset(
    st_row: Dict[str, Any],
    td_by_id: Dict[int, Dict[str, Any]],
    effects_by_id: Dict[int, Dict[str, Any]],
    groups_by_id: Dict[int, Dict[str, Any]],
    cards_by_id: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:
    enemy_td_ids = [int(st_row.get(f"enemy_td_{idx}", 0) or 0) for idx in range(3)]
    enemies = []
    for pos, td_id in enumerate(enemy_td_ids):
        td_row = td_by_id.get(td_id) if td_id else None
        phase_ids = list(td_row.get("phase_ids", []) or []) if td_row else []
        phase_rows = [td_by_id.get(int(pid)) for pid in phase_ids if td_by_id.get(int(pid))]
        enemies.append(
            {
                "pos": pos,
                "td_id": td_id,
                "empty": td_row is None,
                "enemy": td_row,
                "phase_ids": phase_ids,
                "phases": phase_rows,
            }
        )
    def _as_int(value: Any) -> int:
        try:
            return int(value or 0)
        except Exception:
            return 0

    def _best_tag_base() -> int:
        candidates: List[int] = []
        effect_group_id = _as_int(st_row.get("effect_group_id", 0))
        if effect_group_id:
            candidates.append(effect_group_id * 100 + 1)
        tag_group_base = _as_int(st_row.get("tag_group_base_id", 0))
        if tag_group_base:
            candidates.append(tag_group_base)
        vs_id = _as_int(st_row.get("vs_id", 0))
        if vs_id:
            candidates.append(vs_id * 100 + 1)

        best_base = candidates[0] if candidates else 0
        best_count = -1
        for base in dict.fromkeys(candidates):
            count = sum(1 for group_id in range(base, base + 10) if group_id in groups_by_id)
            if count > best_count:
                best_base = base
                best_count = count
        return best_base

    tag_base = _best_tag_base()
    tags = []
    for group_id in range(tag_base, tag_base + 10):
        group = groups_by_id.get(group_id)
        if not group:
            continue
        effect_ids = [int(group.get("effect_id_1", 0) or 0), int(group.get("effect_id_2", 0) or 0)]
        effects = [effects_by_id.get(effect_id, {"kind": 0, "sub_id": 0, "value": 0}) for effect_id in effect_ids if effect_id]
        tag = str(group.get("tag", "") or "").strip()
        if not tag:
            tag = " / ".join(str(effect.get("name") or effect.get("description") or effect.get("effect_id")) for effect in effects)
        tags.append(
            {
                "group_id": group_id,
                "tag": tag,
                "effects": effects,
            }
        )
    card_id = int(st_row.get("card_id", 0) or 0)
    return {
        **st_row,
        "enemy_td_ids": enemy_td_ids,
        "enemies": enemies,
        "tags": tags,
        "drop_card": cards_by_id.get(card_id),
    }


def parse_vs_lua(source_path: Path) -> Dict[str, Any]:
    text = source_path.read_text(encoding="utf-8", errors="replace")
    tribe_reverse_map = _load_tribe_reverse_map(source_path)
    td_rows = [_parse_td(raw, tribe_reverse_map) for raw in _table_rows(text, "td")]
    st_rows = _parse_table(text, "st", ST_FIELD_NAMES)
    card_rows = _parse_table(text, "card", CARD_FIELD_NAMES)
    effect_rows = [_normalize_vs_effect(row) for row in _parse_table(text, "vs_effect", VS_EFFECT_FIELD_NAMES)]
    group_rows = _parse_table(text, "vs_group", VS_GROUP_FIELD_NAMES)

    td_by_id = {int(row.get("td_id", 0)): row for row in td_rows if int(row.get("td_id", 0) or 0)}
    translation_rows = _effect_translation_rows(effect_rows)
    effects_by_id = {int(row.get("effect_id", 0)): _compact_effect(row) for row in effect_rows if int(row.get("effect_id", 0) or 0)}
    groups_by_id = {int(row.get("group_id", 0)): row for row in group_rows if int(row.get("group_id", 0) or 0)}
    cards_by_id = {int(row.get("card_id", 0)): row for row in card_rows if int(row.get("card_id", 0) or 0)}
    presets = [_st_to_preset(row, td_by_id, effects_by_id, groups_by_id, cards_by_id) for row in st_rows]

    return {
        "parser_version": 6,
        "source": str(source_path),
        "row_count": len(td_rows),
        "td_count": len(td_rows),
        "st_count": len(st_rows),
        "card_count": len(card_rows),
        "vs_effect_count": len(effect_rows),
        "vs_group_count": len(group_rows),
        "rows": td_rows,
        "td_rows": td_rows,
        "st_rows": st_rows,
        "card_rows": card_rows,
        "vs_effect_rows": translation_rows,
        "vs_group_rows": group_rows,
        "presets": presets,
    }


def ensure_vs_json(source_path: Path, output_path: Path) -> Dict[str, Any]:
    def write_effect_csv(payload: Dict[str, Any]) -> None:
        project_dir = Path(__file__).resolve().parents[2]
        csv_paths = [
            output_path.with_name("vs_effect_translation.csv"),
            project_dir / "data_tables" / "vs_effect_translation.csv",
        ]
        for csv_path in dict.fromkeys(csv_paths):
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["kind", "sub_id", "value", "name", "description"])
                writer.writeheader()
                for row in payload.get("vs_effect_rows", []):
                    writer.writerow({
                        "kind": row.get("kind", ""),
                        "sub_id": row.get("sub_id", ""),
                        "value": row.get("value", ""),
                        "name": row.get("name", ""),
                        "description": row.get("description", ""),
                    })
    if output_path.exists() and output_path.stat().st_mtime >= source_path.stat().st_mtime:
        with output_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if payload.get("parser_version") == 6 and payload.get("presets") and payload.get("st_count") is not None and payload.get("vs_effect_count") is not None:
            write_effect_csv(payload)
            return payload
    payload = parse_vs_lua(source_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    write_effect_csv(payload)
    return payload
