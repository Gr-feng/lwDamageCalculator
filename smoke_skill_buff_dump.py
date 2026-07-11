# smoke_batch_damage_dump_break_enemy_buffed_ally.py
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

from character import CharacterInstanceManager, Barrier, Buff
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
ENEMY_TRIBE_DEFAULT: List[Any] = [1,2,52,53,54,124,162,181]

QUALITY_INPUT_STRING = "00000000"
QUALITY_LIST = [1, 0, 0, 0, 0, 0, 0, 0, 0]

DEFAULT_FRONT_POS = 0
DEFAULT_ATTACK_TYPE = "5"
DEFAULT_SPIRIT_LEVEL = 3
DEFAULT_TARGET_ENEMY_POS = 0
DEFAULT_SKILL_ORDER = [[0, 0], [0, 1], [0, 2]]
DEFAULT_SHIELD_OPEN_COUNT = 3

ALLY_INITIAL_SPIRIT = 3.0
ALLY_INITIAL_BARRIER_COUNT = 5

ALLY_INITIAL_BUFF_SUB_IDS = [1, 2, 3, 4, 5, 6, 8]
ALLY_INITIAL_BUFF_DURATION = 1
ALLY_INITIAL_BUFF_VALUE = 10

ENEMY_BREAK_BUFFS = [
    (1, 4, 1, -10),
    (1, 2, 1, -10),
]


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


def ensure_dir_for_file(path: str):
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


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


def get_git_hash() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


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
    return ap.parse_args()


# ============================================================
# 枚举文件
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
        "script": "smoke_batch_damage_dump_break_enemy_buffed_ally.py",
        "generated_at": now_iso(),
        "git_hash": get_git_hash(),
        "args": {
            "data_dir": args.data_dir,
            "limit": args.limit,
            "out_summary_csv": args.out_summary_csv,
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
                    "is_break_all": True,
                    "all_barriers_inactive": True,
                    "buffs": [list(x) for x in ENEMY_BREAK_BUFFS],
                }
                for enemy_pos in ENEMY_POSITIONS
            ]
        },
        "ally_setup": {
            "front_pos": DEFAULT_FRONT_POS,
            "initial_spirit": ALLY_INITIAL_SPIRIT,
            "initial_barrier_count": ALLY_INITIAL_BARRIER_COUNT,
            "initial_buffs": [
                [1, sid, ALLY_INITIAL_BUFF_DURATION, ALLY_INITIAL_BUFF_VALUE]
                for sid in ALLY_INITIAL_BUFF_SUB_IDS
            ],
        },
        "op_state": {
            "attack_type": DEFAULT_ATTACK_TYPE,
            "spirit_level_requested": DEFAULT_SPIRIT_LEVEL,
            "enemy_target_pos": DEFAULT_TARGET_ENEMY_POS,
            "skill_order": [list(x) for x in DEFAULT_SKILL_ORDER],
            "shield_open_count": DEFAULT_SHIELD_OPEN_COUNT,
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

    # 敌方初始全破：全部 barrier inactive，is_break_all=True
    inst.barriers = [
        Barrier(barrier_id=i + 1, type=0, is_active=False)
        for i in range(ENEMY_BARRIER_COUNT)
    ]
    inst.is_break_all = True

    # 按你要求的顺序直接写 buffs
    inst.buffs = [
        Buff(buff_id=bid, sub_id=sid, duration=dur, value=val)
        for (bid, sid, dur, val) in ENEMY_BREAK_BUFFS
    ]


def apply_default_ally_overrides(inst):
    # 初始 spirit = 3.0
    inst.update_spirit(float(ALLY_INITIAL_SPIRIT), "set")

    # 初始护盾数 = 5，全部 active，type=0
    inst.barriers = [
        Barrier(barrier_id=i + 1, type=0, is_active=True)
        for i in range(ALLY_INITIAL_BARRIER_COUNT)
    ]
    inst.is_break_all = False

    # 追加我方初始 buffs
    base_buffs = list(getattr(inst, "buffs", []) or [])
    for sid in ALLY_INITIAL_BUFF_SUB_IDS:
        base_buffs.append(
            Buff(
                buff_id=1,
                sub_id=sid,
                duration=ALLY_INITIAL_BUFF_DURATION,
                value=ALLY_INITIAL_BUFF_VALUE,
            )
        )
    inst.buffs = base_buffs


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

def serialize_barriers(barriers):
    out = []
    for b in list(barriers or []):
        out.append({
            "barrier_id": getattr(b, "barrier_id", None),
            "type": getattr(b, "type", None),
            "is_active": getattr(b, "is_active", None),
        })
    return out

def serialize_buffs(buffs):
    out = []
    for b in list(buffs or []):
        out.append({
            "buff_id": getattr(b, "buff_id", None),
            "sub_id": getattr(b, "sub_id", None),
            "duration": getattr(b, "duration", None),
            "value": getattr(b, "value", None),
        })
    return out

def dump_enemy_state_json(mgr, path="./enemy.json"):
    payload = {"enemies": []}
    for enemy_pos in [0, 1, 2]:
        enemy = mgr.get_character_instance("敌方", enemy_pos)
        if enemy is None:
            continue

        info = getattr(enemy, "character_info", {}) or {}
        stats = getattr(enemy, "stats", None)

        payload["enemies"].append({
            "enemy_pos": enemy_pos,
            "id": info.get("id"),
            "name": info.get("name"),
            "tribe": info.get("tribe", []),
            "hp": getattr(stats, "hp", None),
            "yang_def": getattr(stats, "yang_def", None),
            "yin_def": getattr(stats, "yin_def", None),
            "quality": getattr(stats, "quality", None),
            "is_break_all": getattr(enemy, "is_break_all", None),
            "barriers": serialize_barriers(getattr(enemy, "barriers", [])),
            "buffs": serialize_buffs(getattr(enemy, "buffs", [])),
        })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

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
# details 收集 / 汇总
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


def aggregate_yinyang_damage(details: List[Dict[str, Any]]) -> Dict[str, Any]:
    yang_damage = 0
    yin_damage = 0

    for d in details:
        dmg = safe_int(d.get("damage_int", 0))
        yy = d.get("yinyang", None)

        # 当前数据口径：1=阳, 0=阴
        if yy == 1:
            yang_damage += dmg
        elif yy == 0:
            yin_damage += dmg

    total = yang_damage + yin_damage
    if total <= 0:
        yang_ratio = 0.0
        yin_ratio = 0.0
        role = "阴阳均衡"
    else:
        yang_ratio = yang_damage / total
        yin_ratio = yin_damage / total
        if yang_ratio >= 0.7:
            role = "主阳"
        elif yin_ratio >= 0.7:
            role = "主阴"
        else:
            role = "阴阳均衡"

    return {
        "yang_damage_total": yang_damage,
        "yin_damage_total": yin_damage,
        "yang_ratio": yang_ratio,
        "yin_ratio": yin_ratio,
        "yinyang_role": role,
    }


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
) -> Dict[str, Any]:
    agg = aggregate_damage_from_details(details)
    yy = aggregate_yinyang_damage(details)

    return {
        "case_index": case_index,
        "source_file": source_file,
        "character": character,
        "status": "ok",
        "reason": "",
        "seg_damage": agg["seg_damage"],
        "enemy_damage": agg["enemy_damage"],
        "detail_count": len(details),
        "killer_count": count_killer_hits(details),
        "weak_hit_count": count_weak_hits(details),
        "yang_damage_total": yy["yang_damage_total"],
        "yin_damage_total": yy["yin_damage_total"],
        "yang_ratio": yy["yang_ratio"],
        "yin_ratio": yy["yin_ratio"],
        "yinyang_role": yy["yinyang_role"],
        "runtime": runtime,
        "details": details,
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
        "killer_count": 0,
        "weak_hit_count": 0,
        "yang_damage_total": 0,
        "yin_damage_total": 0,
        "yang_ratio": 0.0,
        "yin_ratio": 0.0,
        "yinyang_role": "阴阳均衡",
        "runtime": {},
        "details": [],
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
        "killer_count": 0,
        "weak_hit_count": 0,
        "yang_damage_total": 0,
        "yin_damage_total": 0,
        "yang_ratio": 0.0,
        "yin_ratio": 0.0,
        "yinyang_role": "阴阳均衡",
        "runtime": {},
        "details": [],
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

        mgr, op = create_case_environment(char_data, data_dir=data_dir)
        dump_enemy_state_json(mgr, "./enemy.json")
        apply_default_op_state(op)

        return build_ok_case_result(
            case_index=case_index,
            source_file=source_file,
            character=character,
            runtime=runtime,
            details=details,
        )

    except Exception as e:
        return build_error_case_result(
            case_index=case_index,
            source_file=source_file,
            character=character,
            exc=e,
        )


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
    "ally_initial_buffs",

    "enemy_is_break_all",
    "enemy_break_buffs",

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
    "killer_count",
    "weak_hit_count",

    "yang_damage_total",
    "yin_damage_total",
    "yang_ratio",
    "yin_ratio",
    "yinyang_role",
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
        "ally_initial_buffs": json.dumps(
            [[1, sid, ALLY_INITIAL_BUFF_DURATION, ALLY_INITIAL_BUFF_VALUE] for sid in ALLY_INITIAL_BUFF_SUB_IDS],
            ensure_ascii=False
        ),

        "enemy_is_break_all": True,
        "enemy_break_buffs": json.dumps([list(x) for x in ENEMY_BREAK_BUFFS], ensure_ascii=False),

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
        "killer_count": case_result.get("killer_count", 0),
        "weak_hit_count": case_result.get("weak_hit_count", 0),

        "yang_damage_total": case_result.get("yang_damage_total", 0),
        "yin_damage_total": case_result.get("yin_damage_total", 0),
        "yang_ratio": case_result.get("yang_ratio", 0.0),
        "yin_ratio": case_result.get("yin_ratio", 0.0),
        "yinyang_role": case_result.get("yinyang_role", "阴阳均衡"),
    }


# ============================================================
# 主流程python smoke_skill_buff_dump_v5.py --data-dir ./datajson --limit 400 --out-summary-csv ./summary.csv
# ============================================================

def main():
    args = parse_args()

    meta = build_meta(args)
    _ = meta  # 预留；当前只导出 summary，不单独写 json
    scenario = build_fixed_scenario()
    _ = scenario

    char_files = discover_datajson_files(args.data_dir, args.limit)

    summary_rows: List[Dict[str, Any]] = []

    for idx, char_file in enumerate(char_files, start=1):
        case_result = run_single_case_for_file(
            case_index=idx,
            char_file=char_file,
            data_dir=args.data_dir,
        )
        summary_rows.append(build_summary_row(case_result))

    write_csv(args.out_summary_csv, summary_rows, SUMMARY_FIELDS)

    print(f"[OK] cases={len(summary_rows)}")
    print(f"[OK] summary_csv={args.out_summary_csv}")


if __name__ == "__main__":
    main()