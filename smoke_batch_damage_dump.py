# smoke_batch_damage_dump.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import re
import csv
import json
import argparse
import traceback
import subprocess
from datetime import datetime
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional, Tuple

from character import CharacterInstanceManager, Barrier
from battle_op_state import BattleOpStateManager
from attack_order import get_ally_front_attack_order, parse_attack_segment_order
from damage_pipeline_skeleton import (
    execute_attack_phase_for_attacker,
    assert_A1_gate_once,
    assert_C3_hp_sum,
)


# ============================================================
# 固定场景常量
# ============================================================

ENEMY_ID = 1001
ENEMY_POSITIONS = [0, 2]

ENEMY_HP = 50_000_000
ENEMY_YANG_DEF = 10_000
ENEMY_YIN_DEF = 10_000
ENEMY_BARRIER_COUNT = 9
ENEMY_TRIBE_DEFAULT: List[Any] = []

QUALITY_INPUT_STRING = "00000000"
QUALITY_LIST = [1, 0, 0, 0, 0, 0, 0, 0, 0]

DEFAULT_FRONT_POS = 0
DEFAULT_ATTACK_TYPE = "5"
DEFAULT_SPIRIT_LEVEL = 3
DEFAULT_TARGET_ENEMY_POS = 0
DEFAULT_SKILL_ORDER = [[0, 0], [0, 1], [0, 2]]
DEFAULT_SHIELD_OPEN_COUNT = 3

# 你最新要求：我方初始 spirit=3.0，护盾数=5
ALLY_INITIAL_SPIRIT = 3.0
ALLY_INITIAL_BARRIER_COUNT = 5


# ============================================================
# 基础工具
# ============================================================

def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def ensure_dir(path: str):
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def ensure_dir_for_file(path: str):
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def json_dumps_pretty(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def to_plain_data(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [to_plain_data(x) for x in obj]
    if isinstance(obj, tuple):
        return [to_plain_data(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): to_plain_data(v) for k, v in obj.items()}
    if is_dataclass(obj):
        return to_plain_data(asdict(obj))
    if hasattr(obj, "__dict__"):
        return {str(k): to_plain_data(v) for k, v in vars(obj).items()}
    return str(obj)


def normalize_re(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() == "true"
    return bool(v)


def sanitize_filename(s: str) -> str:
    s = str(s or "").strip()
    s = re.sub(r'[\\/:*?"<>|]+', "_", s)
    s = re.sub(r"\s+", "_", s)
    return s


def get_git_hash() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def write_json(path: str, payload: Dict[str, Any]):
    ensure_dir_for_file(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json_dumps_pretty(payload))


def write_csv(path: str, rows: List[Dict[str, Any]], fieldnames: List[str]):
    ensure_dir_for_file(path)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


# ============================================================
# 参数
# ============================================================

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="./datajson", help="角色 datajson 文件夹")
    ap.add_argument("--limit", type=int, default=10, help="只跑前 N 个；<=0 表示全量")
    ap.add_argument("--out-summary-csv", default="./summary.csv")
    ap.add_argument("--damage-data-dir", default="./damage_data")
    return ap.parse_args()


# ============================================================
# 发现角色文件
# ============================================================

def discover_datajson_files(data_dir: str, limit: int) -> List[str]:
    files = []
    for name in os.listdir(data_dir):
        if not name.endswith(".json"):
            continue
        stem = name[:-5]
        if not stem.isdigit():
            continue
        files.append(os.path.join(data_dir, name))

    files.sort(key=lambda p: int(os.path.splitext(os.path.basename(p))[0]))

    if limit and limit > 0:
        files = files[:limit]
    return files


def load_json_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# meta / scenario
# ============================================================

def build_meta(args) -> Dict[str, Any]:
    return {
        "script": "smoke_batch_damage_dump.py",
        "generated_at": now_iso(),
        "git_hash": get_git_hash(),
        "args": {
            "data_dir": args.data_dir,
            "limit": args.limit,
            "out_summary_csv": args.out_summary_csv,
            "damage_data_dir": args.damage_data_dir,
        },
    }


def build_fixed_scenario() -> Dict[str, Any]:
    return {
        "enemy_setup": {
            "enemies": [
                {
                    "enemy_pos": enemy_pos,
                    "character_id": ENEMY_ID,
                    "hp": ENEMY_HP,
                    "yang_def": ENEMY_YANG_DEF,
                    "yin_def": ENEMY_YIN_DEF,
                    "barrier_count": ENEMY_BARRIER_COUNT,
                    "tribe": list(ENEMY_TRIBE_DEFAULT),
                    "quality": {
                        "input_string": QUALITY_INPUT_STRING,
                        "parsed_list_runtime": list(QUALITY_LIST),
                    },
                }
                for enemy_pos in ENEMY_POSITIONS
            ]
        },
        "ally_setup": {
            "front_pos": DEFAULT_FRONT_POS,
            "initial_spirit": ALLY_INITIAL_SPIRIT,
            "initial_barrier_count": ALLY_INITIAL_BARRIER_COUNT,
        },
        "op_state": {
            "attack_type": DEFAULT_ATTACK_TYPE,
            "spirit_level_requested": DEFAULT_SPIRIT_LEVEL,
            "enemy_target_pos": DEFAULT_TARGET_ENEMY_POS,
            "skill_order": [list(x) for x in DEFAULT_SKILL_ORDER],
            "shield_open_count": DEFAULT_SHIELD_OPEN_COUNT,
        },
        "json_export_rule": {
            "keep_only_first_launch": True,
            "keep_only_hit_damage": True,
            "hit_rule": "debug.first == True and damage_int > 0 and hit_correction > 0",
        },
    }


# ============================================================
# 角色信息
# ============================================================

def extract_character_meta(char_data: Dict[str, Any], source_file: str) -> Dict[str, Any]:
    info = char_data.get("character_info", {}) or {}
    default_id = os.path.splitext(os.path.basename(source_file))[0]
    return {
        "id": safe_int(info.get("id", default_id)),
        "name": str(info.get("name", "") or ""),
        "world_group": str(info.get("world_group", "") or ""),
        "type": info.get("type", ""),
        "re": normalize_re(info.get("re", False)),
    }


def build_damage_json_filename(character: Dict[str, Any]) -> str:
    cid = sanitize_filename(character.get("id", ""))
    name = sanitize_filename(character.get("name", ""))
    wg = sanitize_filename(character.get("world_group", ""))
    return f"{cid}_{name}_{wg}.json"


# ============================================================
# 环境构造
# ============================================================

def apply_default_enemy_overrides(inst):
    inst.stats.hp = ENEMY_HP
    inst.stats.yang_def = ENEMY_YANG_DEF
    inst.stats.yin_def = ENEMY_YIN_DEF
    inst.stats.quality = list(QUALITY_LIST)
    try:
        inst.character_info["tribe"] = list(ENEMY_TRIBE_DEFAULT)
    except Exception:
        pass


def apply_default_ally_overrides(inst):
    # 初始 spirit = 3.0
    inst.update_spirit(float(ALLY_INITIAL_SPIRIT), "set")

    # 初始护盾数 = 5，全部 active，type=0
    inst.barriers = [
        Barrier(barrier_id=i + 1, type=0, is_active=True)
        for i in range(ALLY_INITIAL_BARRIER_COUNT)
    ]
    inst.is_break_all = False


def create_case_environment(
    attacker_char_data: Dict[str, Any],
    data_dir: str,
) -> Tuple[CharacterInstanceManager, BattleOpStateManager]:
    mgr = CharacterInstanceManager()
    op = BattleOpStateManager()

    # 我方：只放 front_pos=0 一个被测角色
    mgr.add_ally_character(position=DEFAULT_FRONT_POS, char_data=attacker_char_data)
    ally = mgr.get_character_instance("我方前排", DEFAULT_FRONT_POS)
    if ally is not None:
        apply_default_ally_overrides(ally)

    # 敌方：固定 0 / 2
    for enemy_pos in ENEMY_POSITIONS:
        mgr.add_enemy_by_id(
            position=enemy_pos,
            character_id=ENEMY_ID,
            data_dir=data_dir,
            yang_def_override=ENEMY_YANG_DEF,
            yin_def_override=ENEMY_YIN_DEF,
            hp_override=ENEMY_HP,
            barrier_count=ENEMY_BARRIER_COUNT,
        )
        enemy = mgr.get_character_instance("敌方", enemy_pos)
        if enemy is not None:
            apply_default_enemy_overrides(enemy)

    return mgr, op


def apply_default_op_state(op: BattleOpStateManager):
    op.set_enemy_target_pos(DEFAULT_FRONT_POS, DEFAULT_TARGET_ENEMY_POS)
    op.set_skill_order([list(x) for x in DEFAULT_SKILL_ORDER])
    op.set_shield_open_count(DEFAULT_FRONT_POS, DEFAULT_SHIELD_OPEN_COUNT)
    op.set_attack_params(DEFAULT_FRONT_POS, DEFAULT_ATTACK_TYPE, DEFAULT_SPIRIT_LEVEL)


# ============================================================
# 执行单 case
# ============================================================

def capture_enemy_hp_map(mgr: CharacterInstanceManager) -> Dict[int, int]:
    out = {}
    for ep in [0, 1, 2]:
        enemy = mgr.get_character_instance("敌方", ep)
        if enemy is not None:
            out[ep] = safe_int(enemy.stats.hp)
    return out


def run_single_case(
    mgr: CharacterInstanceManager,
    op: BattleOpStateManager,
) -> Dict[str, Any]:
    ally_front_chars = [
        mgr.get_character_instance("我方前排", 0),
        mgr.get_character_instance("我方前排", 1),
        mgr.get_character_instance("我方前排", 2),
    ]
    enemy_chars = [
        mgr.get_character_instance("敌方", 0),
        mgr.get_character_instance("敌方", 1),
        mgr.get_character_instance("敌方", 2),
    ]

    result = {
        "success": True,
        "errors": [],
        "skill_execution": [],
        "shield_execution": [],
        "spirit_execution": [],
        "pre_attack_buff_execution": [],
        "post_attack_buff_execution": [],
    }

    op._execute_skills(mgr, ally_front_chars, enemy_chars, result)
    op._execute_shields(mgr, ally_front_chars, result)
    op._execute_spirit(mgr, ally_front_chars, result)

    order, snapshot = get_ally_front_attack_order(mgr, return_debug=True)

    attack_turns: List[Dict[str, Any]] = []

    for turn_idx, attacker_pos in enumerate(order, start=1):
        attacker = mgr.get_character_instance("我方前排", attacker_pos)
        if attacker is None:
            continue

        op_status = op.get_op_status(attacker_pos)
        attack_type = op_status.attack_type
        spirit_level = safe_int(getattr(op_status, "spirit_level", 0))

        turn_rec: Dict[str, Any] = {
            "turn_idx": turn_idx,
            "attacker_pos": attacker_pos,
            "attack_type": attack_type,
            "spirit_level": spirit_level,
            "status": "ok",
            "reason": "",
            "segment_order": [],
            "before_hp_map": {},
            "after_hp_map": {},
            "pre_attack_result": None,
            "post_attack_result": None,
            "details": [],
        }

        if attack_type not in (attacker.attack_skills or {}):
            turn_rec["status"] = "skipped"
            turn_rec["reason"] = f"缺少 attack_type={attack_type}"
            attack_turns.append(turn_rec)
            continue

        attack_skill_data = attacker.attack_skills[attack_type]
        segment_order = parse_attack_segment_order(attack_skill_data, spirit_level)
        turn_rec["segment_order"] = list(segment_order)

        before_hp_map = capture_enemy_hp_map(mgr)
        turn_rec["before_hp_map"] = dict(before_hp_map)

        pre_ret = op.execute_pre_attack_buffs_for_attacker(mgr, attacker_pos, result)
        turn_rec["pre_attack_result"] = to_plain_data(pre_ret)

        details = execute_attack_phase_for_attacker(
            mgr,
            op,
            attacker_pos=attacker_pos,
            segment_order=segment_order,
            debug_print=False,
        )
        turn_rec["details"] = to_plain_data(details)

        post_ret = op.execute_post_attack_buffs_for_attacker(mgr, attacker_pos, result)
        turn_rec["post_attack_result"] = to_plain_data(post_ret)

        after_hp_map = capture_enemy_hp_map(mgr)
        turn_rec["after_hp_map"] = dict(after_hp_map)

        try:
            assert_A1_gate_once(details)
        except Exception as e:
            turn_rec.setdefault("assertions", []).append({
                "name": "assert_A1_gate_once",
                "ok": False,
                "error": repr(e),
            })
        else:
            turn_rec.setdefault("assertions", []).append({
                "name": "assert_A1_gate_once",
                "ok": True,
            })

        for ep, hp_before in before_hp_map.items():
            try:
                assert_C3_hp_sum(mgr, ep, hp_before, details)
            except Exception as e:
                turn_rec.setdefault("assertions", []).append({
                    "name": f"assert_C3_hp_sum_enemy_{ep}",
                    "ok": False,
                    "error": repr(e),
                })
            else:
                turn_rec.setdefault("assertions", []).append({
                    "name": f"assert_C3_hp_sum_enemy_{ep}",
                    "ok": True,
                })

        attack_turns.append(turn_rec)

    return {
        "op_result": to_plain_data(result),
        "attack_order": list(order),
        "attack_order_snapshot": to_plain_data(snapshot),
        "attack_turns": attack_turns,
    }


# ============================================================
# details 收集 / 过滤 / 汇总
# ============================================================

def collect_all_details(runtime: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for turn in runtime.get("attack_turns", []) or []:
        for d in turn.get("details", []) or []:
            row = dict(d)
            row["_turn_idx"] = turn.get("turn_idx")
            row["_turn_attacker_pos"] = turn.get("attacker_pos")
            row["_turn_attack_type"] = turn.get("attack_type")
            row["_turn_spirit_level"] = turn.get("spirit_level")
            out.append(row)
    return out


def is_kept_json_detail(d: Dict[str, Any]) -> bool:
    """
    只保留：
    1) 首发判定命中的那一发
    2) 没命中的不进 JSON
    当前口径：
      - debug.first == True
      - damage_int > 0
      - hit_correction > 0
    """
    debug = d.get("debug", {}) or {}
    first = bool(debug.get("first", False))
    damage_int = safe_int(d.get("damage_int", 0))
    hit_correction = safe_float(d.get("hit_correction", 0.0))
    return first and damage_int > 0 and hit_correction > 0


def build_json_export_details(details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    kept = []
    for d in details:
        if not is_kept_json_detail(d):
            continue

        kept.append({
            "turn_idx": d.get("_turn_idx"),
            "attacker_pos": d.get("attacker_pos"),
            "attack_type": d.get("attack_type"),
            "spirit_level": d.get("spirit_level"),
            "seg": d.get("seg"),
            "enemy_pos": d.get("enemy_pos"),

            "shot_name": d.get("shot_name"),
            "attack_id": d.get("attack_id"),
            "bullet_type": d.get("bullet_type"),
            "element": d.get("element"),
            "yinyang": d.get("yinyang"),
            "killers": d.get("killers", []),

            "def_type": d.get("def_type"),
            "power": d.get("power"),
            "level_mult": d.get("level_mult"),
            "danmaku_mult": d.get("danmaku_mult"),

            "base_atk": d.get("base_atk"),
            "base_def": d.get("base_def"),
            "base_damage": d.get("base_damage"),

            "hit_correction": d.get("hit_correction"),
            "crit_correction": d.get("crit_correction"),
            "element_correction": d.get("element_correction"),
            "bullet_type_correction": d.get("bullet_type_correction"),
            "other_correction": d.get("other_correction"),
            "buff54_damage_correction": d.get("buff54_damage_correction"),

            "final_damage": d.get("final_damage"),
            "damage_int": d.get("damage_int"),
            "before_hp": d.get("before_hp"),
            "after_hp": d.get("after_hp"),

            "hit": d.get("hit", {}),
            "atk_info": d.get("atk_info", {}),
            "def_info": d.get("def_info", {}),
            "element_info": d.get("element_info", {}),
            "bullet_type_info": d.get("bullet_type_info", {}),
            "buff47_info": d.get("buff47_info", {}),
            "buff48_info": d.get("buff48_info", {}),

            "pre_barrier_stock": d.get("pre_barrier_stock"),
            "pre_spirit_stock": d.get("pre_spirit_stock"),

            "flags": d.get("flags", {}),
            "unhandled_effects": d.get("unhandled_effects", []),
            "debug": d.get("debug", {}),
        })
    return kept


def aggregate_damage_from_details(details: List[Dict[str, Any]]) -> Dict[str, Any]:
    seg_damage = {f"seg{i}": 0 for i in range(6)}
    enemy_damage = {
        "enemy_pos_0": 0,
        "enemy_pos_2": 0,
        "overall": 0,
    }

    for d in details:
        dmg = safe_int(d.get("damage_int", 0))
        seg = safe_int(d.get("seg", -1), -1)
        enemy_pos = safe_int(d.get("enemy_pos", -1), -1)

        if 0 <= seg < 6:
            seg_damage[f"seg{seg}"] += dmg

        if enemy_pos == 0:
            enemy_damage["enemy_pos_0"] += dmg
        elif enemy_pos == 2:
            enemy_damage["enemy_pos_2"] += dmg

        enemy_damage["overall"] += dmg

    return {
        "seg_damage": seg_damage,
        "enemy_damage": enemy_damage,
    }


def count_killer_hits(details: List[Dict[str, Any]]) -> int:
    cnt = 0
    for d in details:
        hit = d.get("hit", {}) or {}
        if bool(hit.get("killer", False)):
            cnt += 1
    return cnt


def count_weak_hits(details: List[Dict[str, Any]]) -> int:
    cnt = 0
    for d in details:
        ei = d.get("element_info", {}) or {}
        quality_value = ei.get("quality_value", None)
        element_mode = ei.get("element_mode", "")
        if quality_value == 0 or element_mode == "advantage":
            cnt += 1
    return cnt


def get_actual_spirit_level_from_runtime(runtime: Dict[str, Any]) -> Optional[int]:
    turns = runtime.get("attack_turns", []) or []
    if not turns:
        return None
    return safe_int(turns[0].get("spirit_level"))


# ============================================================
# result 构造
# ============================================================

def build_ok_case_result(
    case_index: int,
    source_file: str,
    character: Dict[str, Any],
    runtime: Dict[str, Any],
    details: List[Dict[str, Any]],
    json_kept_details: List[Dict[str, Any]],
) -> Dict[str, Any]:
    agg = aggregate_damage_from_details(details)
    return {
        "case_index": case_index,
        "source_file": source_file,
        "character": character,
        "status": "ok",
        "reason": "",
        "seg_damage": agg["seg_damage"],
        "enemy_damage": agg["enemy_damage"],
        "detail_count": len(details),
        "json_kept_count": len(json_kept_details),
        "killer_count": count_killer_hits(details),
        "weak_hit_count": count_weak_hits(details),
        "runtime": runtime,
        "details": details,
        "json_kept_details": json_kept_details,
    }


def build_skipped_case_result(
    case_index: int,
    source_file: str,
    character: Dict[str, Any],
    reason: str,
) -> Dict[str, Any]:
    return {
        "case_index": case_index,
        "source_file": source_file,
        "character": character,
        "status": "skipped",
        "reason": reason,
        "seg_damage": {f"seg{i}": 0 for i in range(6)},
        "enemy_damage": {
            "enemy_pos_0": 0,
            "enemy_pos_2": 0,
            "overall": 0,
        },
        "detail_count": 0,
        "json_kept_count": 0,
        "killer_count": 0,
        "weak_hit_count": 0,
        "runtime": {},
        "details": [],
        "json_kept_details": [],
    }


def build_error_case_result(
    case_index: int,
    source_file: str,
    character: Dict[str, Any],
    exc: Exception,
) -> Dict[str, Any]:
    return {
        "case_index": case_index,
        "source_file": source_file,
        "character": character,
        "status": "error",
        "reason": repr(exc),
        "traceback": traceback.format_exc(),
        "seg_damage": {f"seg{i}": 0 for i in range(6)},
        "enemy_damage": {
            "enemy_pos_0": 0,
            "enemy_pos_2": 0,
            "overall": 0,
        },
        "detail_count": 0,
        "json_kept_count": 0,
        "killer_count": 0,
        "weak_hit_count": 0,
        "runtime": {},
        "details": [],
        "json_kept_details": [],
    }


def run_single_case_for_file(
    case_index: int,
    char_file: str,
    data_dir: str,
) -> Dict[str, Any]:
    source_file = os.path.basename(char_file)
    char_data = load_json_file(char_file)
    character = extract_character_meta(char_data, source_file)

    try:
        attack_skills = char_data.get("attack_skills", {}) or {}
        if DEFAULT_ATTACK_TYPE not in attack_skills:
            return build_skipped_case_result(
                case_index=case_index,
                source_file=source_file,
                character=character,
                reason=f"缺少 attack_skills['{DEFAULT_ATTACK_TYPE}']",
            )

        mgr, op = create_case_environment(char_data, data_dir=data_dir)
        apply_default_op_state(op)

        runtime = run_single_case(mgr, op)
        details = collect_all_details(runtime)
        json_kept_details = build_json_export_details(details)

        return build_ok_case_result(
            case_index=case_index,
            source_file=source_file,
            character=character,
            runtime=runtime,
            details=details,
            json_kept_details=json_kept_details,
        )

    except Exception as e:
        return build_error_case_result(
            case_index=case_index,
            source_file=source_file,
            character=character,
            exc=e,
        )


# ============================================================
# 每角色 JSON 导出
# ============================================================

def build_per_character_json_payload(
    meta: Dict[str, Any],
    scenario: Dict[str, Any],
    case_result: Dict[str, Any],
) -> Dict[str, Any]:
    character = case_result.get("character", {}) or {}
    runtime = case_result.get("runtime", {}) or {}

    payload = {
        "meta": meta,
        "scenario": scenario,
        "character": character,
        "case": {
            "case_index": case_result.get("case_index"),
            "source_file": case_result.get("source_file"),
            "status": case_result.get("status"),
            "reason": case_result.get("reason", ""),
        },
        "summary": {
            "seg_damage": case_result.get("seg_damage", {}),
            "enemy_damage": case_result.get("enemy_damage", {}),
            "detail_count": case_result.get("detail_count", 0),
            "json_kept_count": case_result.get("json_kept_count", 0),
            "killer_count": case_result.get("killer_count", 0),
            "weak_hit_count": case_result.get("weak_hit_count", 0),
            "attack_order": runtime.get("attack_order", []),
        },
        # 这里不再塞全量 details，只保留首发且命中的那一发
        "details": case_result.get("json_kept_details", []),
    }
    return payload


def write_per_character_json(
    damage_data_dir: str,
    meta: Dict[str, Any],
    scenario: Dict[str, Any],
    case_result: Dict[str, Any],
):
    character = case_result.get("character", {}) or {}
    filename = build_damage_json_filename(character)
    path = os.path.join(damage_data_dir, filename)

    payload = build_per_character_json_payload(meta, scenario, case_result)
    write_json(path, payload)


# ============================================================
# summary.csv
# ============================================================

SUMMARY_FIELDS = [
    "case_index",
    "source_file",
    "character_id",
    "character_name",
    "world_group",
    "type",
    "re",
    "status",
    "reason",

    "attack_type",
    "spirit_level_requested",
    "spirit_level_actual",
    "target_enemy_pos",

    "ally_initial_spirit",
    "ally_initial_barrier_count",

    "seg0",
    "seg1",
    "seg2",
    "seg3",
    "seg4",
    "seg5",

    "enemy_pos_0_total",
    "enemy_pos_2_total",
    "overall_total",

    "detail_count",
    "json_kept_count",
    "killer_count",
    "weak_hit_count",

    "damage_json_file",
]


def build_summary_row(case_result: Dict[str, Any]) -> Dict[str, Any]:
    ch = case_result.get("character", {}) or {}
    runtime = case_result.get("runtime", {}) or {}
    seg_damage = case_result.get("seg_damage", {}) or {}
    enemy_damage = case_result.get("enemy_damage", {}) or {}

    return {
        "case_index": case_result.get("case_index", ""),
        "source_file": case_result.get("source_file", ""),
        "character_id": ch.get("id", ""),
        "character_name": ch.get("name", ""),
        "world_group": ch.get("world_group", ""),
        "type": ch.get("type", ""),
        "re": ch.get("re", ""),
        "status": case_result.get("status", ""),
        "reason": case_result.get("reason", ""),

        "attack_type": DEFAULT_ATTACK_TYPE,
        "spirit_level_requested": DEFAULT_SPIRIT_LEVEL,
        "spirit_level_actual": get_actual_spirit_level_from_runtime(runtime),
        "target_enemy_pos": DEFAULT_TARGET_ENEMY_POS,

        "ally_initial_spirit": ALLY_INITIAL_SPIRIT,
        "ally_initial_barrier_count": ALLY_INITIAL_BARRIER_COUNT,

        "seg0": seg_damage.get("seg0", 0),
        "seg1": seg_damage.get("seg1", 0),
        "seg2": seg_damage.get("seg2", 0),
        "seg3": seg_damage.get("seg3", 0),
        "seg4": seg_damage.get("seg4", 0),
        "seg5": seg_damage.get("seg5", 0),

        "enemy_pos_0_total": enemy_damage.get("enemy_pos_0", 0),
        "enemy_pos_2_total": enemy_damage.get("enemy_pos_2", 0),
        "overall_total": enemy_damage.get("overall", 0),

        "detail_count": case_result.get("detail_count", 0),
        "json_kept_count": case_result.get("json_kept_count", 0),
        "killer_count": case_result.get("killer_count", 0),
        "weak_hit_count": case_result.get("weak_hit_count", 0),

        "damage_json_file": build_damage_json_filename(ch),
    }


# ============================================================
# 主流程
# ============================================================

def main():
    args = parse_args()

    ensure_dir(args.damage_data_dir)

    meta = build_meta(args)
    scenario = build_fixed_scenario()
    char_files = discover_datajson_files(args.data_dir, args.limit)

    summary_rows: List[Dict[str, Any]] = []

    for idx, char_file in enumerate(char_files, start=1):
        case_result = run_single_case_for_file(
            case_index=idx,
            char_file=char_file,
            data_dir=args.data_dir,
        )

        summary_rows.append(build_summary_row(case_result))
        write_per_character_json(
            damage_data_dir=args.damage_data_dir,
            meta=meta,
            scenario=scenario,
            case_result=case_result,
        )

    write_csv(args.out_summary_csv, summary_rows, SUMMARY_FIELDS)

    print(f"[OK] cases={len(summary_rows)}")
    print(f"[OK] summary_csv={args.out_summary_csv}")
    print(f"[OK] damage_data_dir={args.damage_data_dir}")


if __name__ == "__main__":
    main()