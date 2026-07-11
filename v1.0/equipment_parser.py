from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


BASE_DIR = Path(__file__).resolve().parent
SOURCE_TXT_PATH = BASE_DIR / "绘卷buff03-26.txt"
CN_SOURCE_TXT_PATH = BASE_DIR / "绘卷buff04-04国服.txt"
D_SOURCE_TXT_PATH = BASE_DIR / "D绘卷.txt"
OUTPUT_JSON_PATH = BASE_DIR / "equipment_data.json"

CARD_STYLE_LABELS = {
    0: "D",
    1: "梅",
    2: "兰",
    3: "菊",
    4: "竹",
}

EQUIPMENT_STAT_CODE_MAP = {
    1: {"label": "HP", "stats_key": "hp"},
    2: {"label": "阳攻", "stats_key": "yang_atk"},
    3: {"label": "阳防", "stats_key": "yang_def"},
    4: {"label": "阴攻", "stats_key": "yin_atk"},
    5: {"label": "阴防", "stats_key": "yin_def"},
    6: {"label": "速度", "stats_key": "spd"},
}


def read_source_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp932", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _skip_ws(text: str, idx: int) -> int:
    while idx < len(text) and text[idx].isspace():
        idx += 1
    return idx


def _parse_string(text: str, idx: int) -> Tuple[str, int]:
    idx += 1
    out: List[str] = []
    while idx < len(text):
        ch = text[idx]
        if ch == "\\" and idx + 1 < len(text):
            out.append(text[idx + 1])
            idx += 2
            continue
        if ch == '"':
            return "".join(out), idx + 1
        out.append(ch)
        idx += 1
    raise ValueError("unterminated string")


def _parse_number(text: str, idx: int) -> Tuple[Any, int]:
    start = idx
    if text[idx] in "+-":
        idx += 1
    while idx < len(text) and (text[idx].isdigit() or text[idx] == "."):
        idx += 1
    token = text[start:idx]
    if "." in token:
        return token, idx
    return int(token), idx


def _parse_value(text: str, idx: int) -> Tuple[Any, int]:
    idx = _skip_ws(text, idx)
    if idx >= len(text):
        raise ValueError("unexpected eof")
    ch = text[idx]
    if ch == "{":
        return _parse_array(text, idx)
    if ch == '"':
        return _parse_string(text, idx)
    if ch.isdigit() or ch in "+-":
        return _parse_number(text, idx)
    raise ValueError(f"unexpected token at {idx}: {ch!r}")


def _parse_array(text: str, idx: int) -> Tuple[List[Any], int]:
    if text[idx] != "{":
        raise ValueError("array must start with '{'")
    idx += 1
    values: List[Any] = []
    while True:
        idx = _skip_ws(text, idx)
        if idx >= len(text):
            raise ValueError("unterminated array")
        if text[idx] == "}":
            return values, idx + 1
        value, idx = _parse_value(text, idx)
        values.append(value)
        idx = _skip_ws(text, idx)
        if idx < len(text) and text[idx] == ",":
            idx += 1


def _normalize_equipment_identity(raw_value: Any) -> Dict[str, Any]:
    raw_text = str(raw_value).strip()
    if "." not in raw_text:
        equipment_id = int(raw_text)
        return {
            "equipment_id": equipment_id,
            "equipment_id_text": raw_text,
            "equipment_base_id": equipment_id,
            "equipment_variant_sub_id": 0,
            "is_d_equipment": False,
        }
    base_text, sub_text_raw = raw_text.split(".", 1)
    sub_text = f"{sub_text_raw}0" if len(sub_text_raw) == 1 else sub_text_raw
    base_id = int(base_text)
    variant_sub_id = int(sub_text)
    return {
        "equipment_id": base_id * 1000 + variant_sub_id,
        "equipment_id_text": f"{base_text}.{sub_text}",
        "equipment_id_source_text": raw_text,
        "equipment_base_id": base_id,
        "equipment_variant_sub_id": variant_sub_id,
        "is_d_equipment": True,
    }


def _normalize_effect(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, list) or len(raw) != 5:
        return {
            "raw_id": 0,
            "buff_id": 0,
            "sub_id": 0,
            "value": 0,
            "duration": 0,
            "target_type_raw": 0,
            "target_type": 1,
            "condition_type": 0,
            "exclusive_only": False,
            "ignored": True,
        }

    raw_id = int(raw[0])
    sub_id = int(raw[1])
    value = float(raw[2])
    duration = int(raw[3])
    target_type_raw = int(raw[4])

    buff_id = raw_id
    condition_type = 0
    exclusive_only = False

    if 21 <= raw_id <= 28:
        condition_type = raw_id - 20
        buff_id = 1
    elif 31 <= raw_id <= 38:
        condition_type = raw_id - 30
        buff_id = 2
    elif raw_id >= 2000:
        buff_id = raw_id - 2000
        exclusive_only = True

    target_type = {
        0: 1,
        1: 1,
        2: 2,
        3: 3,
        4: 4,
    }.get(target_type_raw, 1)

    return {
        "raw_id": raw_id,
        "buff_id": int(buff_id),
        "sub_id": sub_id,
        "value": value,
        "duration": duration,
        "target_type_raw": target_type_raw,
        "target_type": target_type,
        "condition_type": condition_type,
        "exclusive_only": exclusive_only,
        "ignored": raw_id == 14 or buff_id == 14 or raw_id == 0,
    }


def _normalize_stats(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    values = list(raw)
    out: List[Dict[str, Any]] = []
    for i in range(0, len(values), 2):
        if i + 1 >= len(values):
            break
        code = int(values[i])
        value = int(values[i + 1])
        if code <= 0 or value == 0:
            continue
        meta = EQUIPMENT_STAT_CODE_MAP.get(code, {})
        out.append(
            {
                "code": code,
                "value": value,
                "label": meta.get("label", f"未知({code})"),
                "stats_key": meta.get("stats_key", ""),
            }
        )
    return out


def parse_record(line: str) -> Dict[str, Any]:
    values, idx = _parse_array(line.strip().rstrip(","), 0)
    idx = _skip_ws(line, idx)
    if len(values) not in (8, 10):
        raise ValueError(f"unexpected equipment field count: {len(values)}")

    identity = _normalize_equipment_identity(values[0])
    name = str(values[1])
    raw_effects = [values[2], values[3], values[4]]
    rarity_sort = int(values[5])
    raw_stats = values[6]
    card_type_code = int(values[7])

    if len(values) == 10:
        obtain_flag = int(values[8])
        exclusive_character_id = int(values[9])
        style_code = int(card_type_code // 10)
        stars = int(card_type_code % 10)
    else:
        obtain_flag = 1
        exclusive_character_id = 0
        style_code = 0
        stars = 5

    return {
        **identity,
        "name": name,
        "effects": [_normalize_effect(raw) for raw in raw_effects],
        "rarity_sort": rarity_sort,
        "stats": _normalize_stats(raw_stats),
        "card_type_code": card_type_code,
        "card_style_code": style_code,
        "card_style_label": CARD_STYLE_LABELS.get(style_code, ""),
        "stars": stars,
        "is_normal_obtain": bool(obtain_flag),
        "obtain_flag": obtain_flag,
        "exclusive_character_id": exclusive_character_id,
    }


def parse_equipment_text(text: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or not stripped.startswith("{"):
            continue
        items.append(parse_record(stripped))
    items.sort(key=lambda item: int(item["equipment_id"]))
    return items


def load_equipment_items(path: Path) -> List[Dict[str, Any]]:
    return parse_equipment_text(read_source_text(path))


def merge_equipment_items(
    base_items: List[Dict[str, Any]],
    cn_items: List[Dict[str, Any]],
    d_items: List[Dict[str, Any]],
) -> List[Dict[int, Dict[str, Any]]]:
    merged: Dict[int, Dict[str, Any]] = {int(item["equipment_id"]): dict(item) for item in base_items}

    for item in merged.values():
        item["name_jp"] = str(item.get("name", "") or "")
        item["name_cn"] = ""

    for cn_item in cn_items:
        equipment_id = int(cn_item["equipment_id"])
        cn_name = str(cn_item.get("name", "") or "")
        if equipment_id in merged:
            merged_item = dict(merged[equipment_id])
            merged_item["name_cn"] = cn_name
            if cn_name:
                merged_item["name"] = cn_name
            merged[equipment_id] = merged_item
            continue

        if equipment_id > 10000:
            cn_copy = dict(cn_item)
            cn_copy["name_jp"] = ""
            cn_copy["name_cn"] = cn_name
            merged[equipment_id] = cn_copy

    for d_item in d_items:
        equipment_id = int(d_item["equipment_id"])
        d_copy = dict(d_item)
        d_copy["name_jp"] = str(d_item.get("name", "") or "")
        d_copy["name_cn"] = ""
        merged[equipment_id] = d_copy

    return [merged[key] for key in sorted(merged)]


def write_equipment_json(
    source_path: Path = SOURCE_TXT_PATH,
    output_path: Path = OUTPUT_JSON_PATH,
    cn_source_path: Path = CN_SOURCE_TXT_PATH,
    d_source_path: Path = D_SOURCE_TXT_PATH,
) -> Path:
    base_items = load_equipment_items(source_path)
    cn_items = load_equipment_items(cn_source_path) if cn_source_path.exists() else []
    d_items = load_equipment_items(d_source_path) if d_source_path.exists() else []
    items = merge_equipment_items(base_items, cn_items, d_items)
    payload = {
        "source_file": source_path.name,
        "source_files": [source_path.name]
        + ([cn_source_path.name] if cn_source_path.exists() else [])
        + ([d_source_path.name] if d_source_path.exists() else []),
        "count": len(items),
        "items": items,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def ensure_equipment_data_json(
    source_path: Path = SOURCE_TXT_PATH,
    output_path: Path = OUTPUT_JSON_PATH,
    cn_source_path: Path = CN_SOURCE_TXT_PATH,
    d_source_path: Path = D_SOURCE_TXT_PATH,
) -> Path:
    if output_path.exists():
        return output_path
    return write_equipment_json(
        source_path=source_path,
        output_path=output_path,
        cn_source_path=cn_source_path,
        d_source_path=d_source_path,
    )


if __name__ == "__main__":
    path = write_equipment_json()
    print(path)
