from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ATTACK_FILE_SUFFIXES = {
    "1": "1",
    "1c": "1c",
    "2": "2",
    "2c": "2c",
    "5": "5",
}

GLOBAL_EFFECT_KEYS = ("effect_before", "effect_after", "icon_before", "icon_after", "type_before", "type_after")
ATTACK_LIST_KEYS = {"buff", "effect", "killers", "order"}
ATTACK_NUMERIC_KEYS = {"acc", "amt", "boost", "cri", "damage", "damage_extend", "element", "id", "rate", "target", "type", "yinyang"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import raw LostWord unit key/value files into datajson format.")
    parser.add_argument("--source", type=Path, required=True, help="Raw unit folder, e.g. v1.2/unit260709")
    parser.add_argument("--output", type=Path, required=True, help="Output datajson folder")
    return parser.parse_args()


def parse_scalar(text: str) -> Any:
    value = text.strip()
    if value == "":
        return ""
    if "," in value:
        parts = [part.strip() for part in value.split(",") if part.strip() != ""]
        if parts and all(re.fullmatch(r"-?\d+(?:\.\d+)?", part) for part in parts):
            return [parse_scalar(part) for part in parts]
        return parts
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value.replace("\\n", "\n")


def parse_pair_file(path: Path) -> dict[int, dict[str, Any]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    rows: dict[int, dict[str, Any]] = {}
    idx = 0
    while idx < len(lines):
        key_line = lines[idx].strip()
        idx += 1
        if not key_line or ":" not in key_line:
            continue
        raw_prefix, key = key_line.split(":", 1)
        if not raw_prefix.isdigit() or not key:
            continue
        value = lines[idx] if idx < len(lines) else ""
        idx += 1
        rows.setdefault(int(raw_prefix), {})[key] = parse_scalar(value)
    return rows


def as_list(value: Any) -> list[Any]:
    if value == "" or value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def as_int_list(value: Any) -> list[int]:
    out: list[int] = []
    for item in as_list(value):
        try:
            out.append(int(item))
        except Exception:
            continue
    return out


def parse_unit(path: Path, character_id: int) -> dict[str, Any]:
    rows = parse_pair_file(path)
    info = dict(rows.get(0, {}))
    info["id"] = character_id
    if "tribe" in info:
        info["tribe"] = as_int_list(info["tribe"])
    return info


def parse_skills(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = parse_pair_file(path)
    skills: list[dict[str, Any]] = []
    for skill_id in sorted(idx for idx in rows if idx > 0):
        raw = rows[skill_id]
        skill: dict[str, Any] = {"id": skill_id}
        for key in ("a", "b", "c"):
            skill[key] = as_int_list(raw.get(key, []))
        skill["cd"] = int(raw.get("cd", 0) or 0)
        skill["name"] = raw.get("name", "")
        if raw.get("description"):
            skill["description"] = raw.get("description")
        if raw.get("icon"):
            skill["icon"] = raw.get("icon")
        skills.append(skill)
    return skills


def parse_attack(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    rows = parse_pair_file(path)
    global_raw = rows.get(0, {})
    attacks: list[dict[str, Any]] = []
    for attack_idx in sorted(idx for idx in rows if idx > 0):
        raw = rows[attack_idx]
        attack: dict[str, Any] = {"attack_id": attack_idx}
        for key, value in raw.items():
            if key in ATTACK_LIST_KEYS:
                attack[key] = as_int_list(value)
            elif key in ATTACK_NUMERIC_KEYS:
                attack[key] = parse_scalar(str(value))
            else:
                attack[key] = value
        attacks.append(attack)

    global_attrs: dict[str, Any] = {}
    for key in GLOBAL_EFFECT_KEYS:
        values: list[list[Any]] = []
        for idx in range(1, 6):
            raw_value = global_raw.get(f"{key}_{idx}", "")
            if key.startswith("icon"):
                values.append([str(item) for item in as_list(raw_value) if str(item)])
            else:
                values.append(as_int_list(raw_value))
        if any(values):
            global_attrs[key] = values

    for key, value in global_raw.items():
        if any(key.startswith(f"{prefix}_") for prefix in GLOBAL_EFFECT_KEYS):
            continue
        if key == "break":
            global_attrs[key] = as_int_list(value)
        elif key in {"first_order", "power_rate"}:
            global_attrs[key] = int(value or 0)
        else:
            global_attrs[key] = value

    if attacks:
        global_attrs["damage_extend"] = [attack.get("damage_extend", 100) for attack in attacks]
        global_attrs["target"] = [attack.get("target", 1) for attack in attacks]

    return {
        "global_attributes": global_attrs,
        "attack_count": len(attacks),
        "attacks": attacks,
    }


def parse_costumes(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    rows = parse_pair_file(path)
    return {str(idx): row for idx, row in rows.items() if row}


def parse_chain(path: Path) -> list[Any]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    return as_int_list(parse_scalar(text)) if text else []


def build_character(source: Path, character_id: int) -> dict[str, Any]:
    unit_path = source / f"{character_id}unit"
    attack_skills: dict[str, Any] = {}
    for suffix, attack_key in ATTACK_FILE_SUFFIXES.items():
        attack = parse_attack(source / f"{character_id}{suffix}")
        if attack is not None:
            attack_skills[attack_key] = attack
    payload = {
        "character_info": parse_unit(unit_path, character_id),
        "chain_character": parse_chain(source / f"{character_id}chain"),
        "costumes": parse_costumes(source / f"{character_id}cos"),
        "skills": parse_skills(source / f"{character_id}skill"),
        "attack_skills": attack_skills,
    }
    apply_known_corrections(payload)
    return payload


def apply_known_corrections(payload: dict[str, Any]) -> None:
    character_id = int(payload.get("character_info", {}).get("id", 0) or 0)
    if character_id == 12050:
        for skill in payload.get("skills", []):
            if skill.get("id") == 3 and skill.get("a") == [54, 1205001, 0, 3, 50]:
                skill["a"] = [54, 1205001, 0, 3, 60]


def discover_character_ids(source: Path) -> list[int]:
    ids: set[int] = set()
    for path in source.iterdir():
        match = re.fullmatch(r"(\d+)unit", path.name)
        if match:
            ids.add(int(match.group(1)))
    return sorted(ids)


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    count = 0
    for character_id in discover_character_ids(args.source):
        payload = build_character(args.source, character_id)
        out_path = args.output / f"{character_id}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=4), encoding="utf-8")
        count += 1
    print(f"imported {count} characters into {args.output}")


if __name__ == "__main__":
    main()
