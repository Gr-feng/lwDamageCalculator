from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from combat_constants import BULLET_RAW_TO_BUFF_SUBID, ELEMENT_RAW_TO_BUFF_SUBID, normalized_lookup_keys
from equipment_parser import OUTPUT_JSON_PATH, ensure_equipment_data_json
from gui.config import AllySlotConfig, EnemySlotConfig, ProcessConfig, EQUIPMENT_SLOT_KEYS
from gui.resources import RECOMMENDED_EQUIPMENT_CSV_PATH
from gui.services import DamageCalculatorService


BASE_DIR = Path(__file__).resolve().parent
ATTACK5_CANDIDATES_CSV_PATH = BASE_DIR / "attack5_candidates.csv"
ATTACK_TYPES = EQUIPMENT_SLOT_KEYS
RECOMMENDATION_SLOT_SOURCES = {
    "1a": "1",
    "2a": "2",
    "1b": "1",
    "2b": "2",
    "5": "5",
}


def load_equipment_items() -> List[Dict[str, Any]]:
    ensure_equipment_data_json()
    with open(OUTPUT_JSON_PATH, "r", encoding="utf-8") as f:
        return list((json.load(f).get("items", []) or []))


def has_attack5_bonus(item: Dict[str, Any]) -> bool:
    for effect in item.get("effects", []) or []:
        if effect.get("ignored"):
            continue
        if int(effect.get("buff_id", 0) or 0) in (15, 16):
            return True
    return False


def write_attack5_candidates(items: Iterable[Dict[str, Any]], path: Path = ATTACK5_CANDIDATES_CSV_PATH) -> Path:
    rows: List[Dict[str, Any]] = []
    for item in items:
        effects = []
        for effect in item.get("effects", []) or []:
            if effect.get("ignored"):
                continue
            if int(effect.get("buff_id", 0) or 0) in (15, 16):
                effects.append(
                    f"{int(effect.get('buff_id', 0))}:{int(effect.get('sub_id', 0))}+{int(round(float(effect.get('value', 0) or 0)))}%"
                )
        if not effects:
            continue
        rows.append(
            {
                "equipment_id": int(item["equipment_id"]),
                "equipment_name": str(item.get("name", "") or ""),
                "stats": " / ".join(f"{row.get('label', '')}+{int(row.get('value', 0))}" for row in item.get("stats", []) or []),
                "attack_bonus_effects": " / ".join(effects),
            }
        )
    rows.sort(key=lambda row: int(row["equipment_id"]))
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["equipment_id", "equipment_name", "stats", "attack_bonus_effects"])
        writer.writeheader()
        writer.writerows(rows)
    return path


def build_eval_slots(char_id: int, attack_type: str) -> Tuple[Dict[int, EnemySlotConfig], Dict[int, AllySlotConfig]]:
    enemy_slots = {
        0: EnemySlotConfig(
            enabled=True,
            character_id=1001,
            hp=99_999_999,
            yang_def=1000,
            yin_def=1000,
            barrier_count=9,
            quality=[1] * 9,
            tribe_text="",
            is_break_all=False,
            buffs=[],
        ),
        1: EnemySlotConfig(enabled=False),
        2: EnemySlotConfig(enabled=False),
    }
    spirit_level = 3 if attack_type in {"1c", "2c", "5"} else 0
    ally_slots = {
        0: AllySlotConfig(
            enabled=True,
            character_id=char_id,
            initial_spirit=3.0,
            barrier_count=5,
            skill_order_text="",
            shield_open_count=0,
            attack_type=attack_type,
            spirit_level=spirit_level,
            target_enemy_pos=0,
            buffs=[],
            equipment_ids={key: 0 for key in EQUIPMENT_SLOT_KEYS},
        ),
        1: AllySlotConfig(enabled=False),
        2: AllySlotConfig(enabled=False),
    }
    return enemy_slots, ally_slots


def build_baseline_result(service: DamageCalculatorService, char_id: int, attack_type: str) -> Dict[str, Any]:
    enemy_slots, ally_slots = build_eval_slots(char_id, attack_type)
    return service.run_single(enemy_slots, ally_slots, ProcessConfig(), equipment_mode="panel_only")


def build_item_delta(item: Dict[str, Any]) -> Tuple[Dict[str, float], Dict[int, float], Dict[int, float]]:
    stats_delta = {"hp": 0.0, "yang_atk": 0.0, "yang_def": 0.0, "yin_atk": 0.0, "yin_def": 0.0, "spd": 0.0}
    for row in item.get("stats", []) or []:
        key = str(row.get("stats_key", "") or "").strip()
        if key in stats_delta:
            stats_delta[key] += float(row.get("value", 0) or 0.0)

    bullet_bonus: Dict[int, float] = {}
    element_bonus: Dict[int, float] = {}
    for effect in item.get("effects", []) or []:
        if effect.get("ignored"):
            continue
        buff_id = int(effect.get("buff_id", 0) or 0)
        sub_id = int(effect.get("sub_id", 0) or 0)
        value = float(effect.get("value", 0) or 0.0) / 100.0
        if buff_id == 15:
            bullet_bonus[sub_id] = bullet_bonus.get(sub_id, 0.0) + value
        elif buff_id == 16:
            element_bonus[sub_id] = element_bonus.get(sub_id, 0.0) + value

    return stats_delta, bullet_bonus, element_bonus


def estimate_damage_from_item(
    details: List[Dict[str, Any]],
    item: Dict[str, Any],
    *,
    include_attack_bonus: bool,
) -> float:
    stats_delta, bullet_bonus, element_bonus = build_item_delta(item)
    total = 0.0
    for detail in details:
        atk_info = detail.get("atk_info", {}) or {}
        base_atk = float(detail.get("base_atk", 0.0) or 0.0)
        base_damage = float(detail.get("final_damage", 0.0) or 0.0)
        if base_atk <= 1e-9:
            continue

        def_type = str(detail.get("def_type", "yang") or "yang")
        if def_type == "yang":
            delta_atk = stats_delta["yang_atk"]
            delta_def = stats_delta["yang_def"]
        else:
            delta_atk = stats_delta["yin_atk"]
            delta_def = stats_delta["yin_def"]
        delta_spd = stats_delta["spd"]

        new_base_atk = (
            (float(atk_info.get("atk_panel", 0.0) or 0.0) + delta_atk) * float(atk_info.get("atk_mult", 1.0) or 1.0)
            + (float(atk_info.get("def_panel", 0.0) or 0.0) + delta_def) * float(atk_info.get("def_mult", 1.0) or 1.0) * float(atk_info.get("hard_pct", 0.0) or 0.0)
            + (float(atk_info.get("spd_panel", 0.0) or 0.0) + delta_spd) * float(atk_info.get("spd_mult", 1.0) or 1.0) * float(atk_info.get("slash_pct", 0.0) or 0.0)
        )
        ratio = new_base_atk / base_atk

        if include_attack_bonus:
            bullet_type = int(detail.get("bullet_type", 0) or 0)
            element = int(detail.get("element", 0) or 0)
            bullet_pct = sum(bullet_bonus.get(key, 0.0) for key in normalized_lookup_keys(bullet_type, BULLET_RAW_TO_BUFF_SUBID))
            element_pct = sum(element_bonus.get(key, 0.0) for key in normalized_lookup_keys(element, ELEMENT_RAW_TO_BUFF_SUBID))
            ratio *= (1.0 + bullet_pct) * (1.0 + element_pct)

        total += base_damage * ratio
    return total


def choose_best_item(
    details: List[Dict[str, Any]],
    items: List[Dict[str, Any]],
    *,
    include_attack_bonus: bool,
    seed_text: str,
) -> Tuple[Dict[str, Any], float]:
    baseline = sum(float(detail.get("final_damage", 0.0) or 0.0) for detail in details)
    best_score = baseline
    best_items: List[Dict[str, Any]] = []
    for item in items:
        score = estimate_damage_from_item(details, item, include_attack_bonus=include_attack_bonus)
        if score > best_score + 1e-6:
            best_score = score
            best_items = [item]
        elif abs(score - best_score) <= 1e-6:
            best_items.append(item)
    if not best_items:
        return {"equipment_id": 0, "name": ""}, 1.0
    rng = random.Random(seed_text)
    chosen = rng.choice(sorted(best_items, key=lambda row: int(row.get("equipment_id", 0))))
    ratio = (best_score / baseline) if baseline > 1e-9 else 1.0
    return chosen, ratio


def build_recommended_csv() -> Tuple[Path, Path]:
    items = load_equipment_items()
    candidate_csv_path = write_attack5_candidates(items)
    service = DamageCalculatorService()

    standard_items = [item for item in items if not bool(item.get("is_d_equipment", False))]
    d_items = [item for item in items if bool(item.get("is_d_equipment", False))]
    panel_items = [item for item in standard_items if item.get("stats")]
    attack5_items = [item for item in standard_items if has_attack5_bonus(item)]
    lw_items = [item for item in attack5_items]
    for item in d_items:
        if item not in lw_items:
            lw_items.append(item)

    rows: List[Dict[str, Any]] = []
    for char_id in service.discover_all_ids():
        meta = service.load_character_meta(char_id)
        row: Dict[str, Any] = {
            "character_id": char_id,
            "character_name": meta.get("name", ""),
            "name_cn": service.translate_character_name(meta.get("name", ""), char_id),
            "world_group": meta.get("world_group", ""),
            "character_type": meta.get("type_label", ""),
        }
        best_by_source: Dict[str, Tuple[Dict[str, Any], float]] = {}
        for source_attack_type in ("1", "2", "5"):
            baseline_result = build_baseline_result(service, char_id, source_attack_type)
            details = list(baseline_result.get("details", []) or [])
            include_attack_bonus = source_attack_type == "5"
            candidates = lw_items if include_attack_bonus else panel_items
            best_item, ratio = choose_best_item(
                details,
                candidates,
                include_attack_bonus=include_attack_bonus,
                seed_text=f"{char_id}:{source_attack_type}",
            )
            best_by_source[source_attack_type] = (best_item, ratio)

        for attack_type in ATTACK_TYPES:
            best_item, ratio = best_by_source[RECOMMENDATION_SLOT_SOURCES[attack_type]]
            row[f"equipment_{attack_type}_id"] = int(best_item.get("equipment_id", 0) or 0)
            row[f"equipment_{attack_type}_name"] = str(best_item.get("name", "") or "")
            row[f"equipment_{attack_type}_ratio"] = ratio
        rows.append(row)

    output_path = Path(RECOMMENDED_EQUIPMENT_CSV_PATH)
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "character_id",
            "character_name",
            "name_cn",
            "world_group",
            "character_type",
        ]
        for attack_type in ATTACK_TYPES:
            fieldnames.extend(
                [
                    f"equipment_{attack_type}_id",
                    f"equipment_{attack_type}_name",
                    f"equipment_{attack_type}_ratio",
                ]
            )
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return candidate_csv_path, output_path


if __name__ == "__main__":
    candidate_path, recommended_path = build_recommended_csv()
    print(candidate_path)
    print(recommended_path)
