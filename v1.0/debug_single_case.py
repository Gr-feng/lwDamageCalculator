from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional

from character import CharacterInstanceManager, Barrier, Buff
from battle_op_state import BattleOpStateManager
from attack_order import get_ally_front_attack_order, parse_attack_segment_order
from damage_pipeline_skeleton import execute_attack_phase_for_attacker


# -----------------------------
# serialization helpers
# -----------------------------

def _to_jsonable(x: Any) -> Any:
    if is_dataclass(x):
        return asdict(x)
    if isinstance(x, dict):
        return {str(k): _to_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_to_jsonable(v) for v in x]
    return x


def _buff_group(inst) -> Dict[str, Any]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for b in list(getattr(inst, "buffs", []) or []):
        key = f"{int(getattr(b, 'buff_id', 0))}:{int(getattr(b, 'sub_id', 0))}"
        if key not in grouped:
            grouped[key] = {
                "buff_id": int(getattr(b, "buff_id", 0)),
                "sub_id": int(getattr(b, "sub_id", 0)),
                "entries": 0,
                "sum_value": 0.0,
                "max_duration": 0,
            }
        grouped[key]["entries"] += 1
        grouped[key]["sum_value"] += float(getattr(b, "value", 0.0))
        grouped[key]["max_duration"] = max(grouped[key]["max_duration"], int(getattr(b, "duration", 0)))
    return dict(sorted(grouped.items(), key=lambda kv: (kv[1]["buff_id"], kv[1]["sub_id"])))


def snapshot_character(inst, *, label: str) -> Dict[str, Any]:
    if inst is None:
        return {"label": label, "exists": False}

    s = inst.stats
    return {
        "label": label,
        "exists": True,
        "name": (getattr(inst, "character_info", {}) or {}).get("name", ""),
        "id": (getattr(inst, "character_info", {}) or {}).get("id", (getattr(inst, "character_info", {}) or {}).get("character_id")),
        "base_stats": {
            "yang_atk": int(getattr(s, "yang_atk", 0)),
            "yin_atk": int(getattr(s, "yin_atk", 0)),
            "yang_def": int(getattr(s, "yang_def", 0)),
            "yin_def": int(getattr(s, "yin_def", 0)),
            "spd": int(getattr(s, "spd", 0)),
            "hp": int(getattr(s, "hp", 0)),
        },
        "runtime": {
            "spirit": float(getattr(inst, "spirit", 0.0)),
            "is_break_all": bool(getattr(inst, "is_break_all", False)),
            "is_stunned": bool(getattr(inst, "is_stunned", False)),
            "paragraph_executed": list(getattr(inst, "paragraph_executed", []) or []),
        },
        "barriers": {
            "count": len(list(getattr(inst, "barriers", []) or [])),
            "active_count": sum(1 for b in list(getattr(inst, "barriers", []) or []) if getattr(b, "is_active", False)),
            "items": [
                {
                    "barrier_id": int(getattr(b, "barrier_id", 0)),
                    "type": int(getattr(b, "type", 0)),
                    "is_active": bool(getattr(b, "is_active", False)),
                }
                for b in list(getattr(inst, "barriers", []) or [])
            ],
        },
        "buffs": {
            "raw": [
                {
                    "buff_id": int(getattr(b, "buff_id", 0)),
                    "sub_id": int(getattr(b, "sub_id", 0)),
                    "value": float(getattr(b, "value", 0.0)),
                    "duration": int(getattr(b, "duration", 0)),
                }
                for b in list(getattr(inst, "buffs", []) or [])
            ],
            "grouped": _buff_group(inst),
        },
        "quality": list(getattr(s, "quality", []) or []),
    }


def snapshot_world(mgr: CharacterInstanceManager, attacker_pos: int = 0, target_enemy_pos: int = 0) -> Dict[str, Any]:
    return {
        "attacker": snapshot_character(mgr.get_character_instance("我方前排", attacker_pos), label=f"ally_front_{attacker_pos}"),
        "target_enemy": snapshot_character(mgr.get_character_instance("敌方", target_enemy_pos), label=f"enemy_{target_enemy_pos}"),
        "ally_all": [snapshot_character(mgr.get_character_instance("我方前排", i), label=f"ally_front_{i}") for i in (0, 1, 2)],
        "enemy_all": [snapshot_character(mgr.get_character_instance("敌方", i), label=f"enemy_{i}") for i in (0, 1, 2)],
    }


# -----------------------------
# config loader
# -----------------------------

def parse_buff_rows(rows: List[List[Any]]) -> List[Buff]:
    out: List[Buff] = []
    for row in rows:
        if not row or len(row) < 4:
            continue
        out.append(Buff(buff_id=int(row[0]), sub_id=int(row[1]), duration=int(row[2]), value=float(row[3])))
    return out


def parse_tribe(text: str) -> List[int]:
    vals: List[int] = []
    for part in str(text or "").replace("，", ",").split(","):
        s = part.strip()
        if s:
            vals.append(int(s))
    return vals


def apply_enemy_slot(mgr: CharacterInstanceManager, enemy_pos: int, cfg: Dict[str, Any], data_dir: str):
    if not cfg.get("enabled"):
        return
    mgr.add_enemy_by_id(
        position=enemy_pos,
        character_id=int(cfg["character_id"]),
        data_dir=data_dir,
        yang_def_override=cfg.get("yang_def"),
        yin_def_override=cfg.get("yin_def"),
        hp_override=cfg.get("hp"),
        barrier_count=int(cfg.get("barrier_count", 5)),
    )
    enemy = mgr.get_character_instance("敌方", enemy_pos)
    enemy.stats.hp = int(cfg.get("hp", enemy.stats.hp))
    enemy.stats.yang_def = int(cfg.get("yang_def", enemy.stats.yang_def))
    enemy.stats.yin_def = int(cfg.get("yin_def", enemy.stats.yin_def))
    enemy.stats.quality = [1] + list(cfg.get("quality", [1] * 9))
    enemy.character_info["tribe"] = parse_tribe(cfg.get("tribe_text", ""))
    enemy.barriers = [Barrier(barrier_id=i + 1, type=0, is_active=True) for i in range(int(cfg.get("barrier_count", 5)))]
    enemy.buffs = parse_buff_rows(cfg.get("buffs", []))
    enemy.is_break_all = False
    if cfg.get("is_break_all"):
        for b in enemy.barriers:
            b.is_active = False
            b.type = 0
        enemy.break_all_barrier()


def apply_ally_slot(mgr: CharacterInstanceManager, ally_pos: int, cfg: Dict[str, Any], ally_data: Dict[str, Any]):
    if not cfg.get("enabled"):
        return
    mgr.add_ally_character(position=ally_pos, char_data=ally_data)
    ally = mgr.get_character_instance("我方前排", ally_pos)
    ally.update_spirit(float(cfg.get("initial_spirit", 1.0)), "set")
    ally.barriers = [Barrier(barrier_id=i + 1, type=0, is_active=True) for i in range(int(cfg.get("barrier_count", 5)))]
    ally.is_break_all = False
    ally.buffs = list(getattr(ally, "buffs", []) or []) + parse_buff_rows(cfg.get("buffs", []))


# -----------------------------
# main debug routine
# -----------------------------

def run_debug(preset_path: str, ally_json_path: str, data_dir: Optional[str] = None, out_path: Optional[str] = None) -> Dict[str, Any]:
    with open(preset_path, "r", encoding="utf-8") as f:
        preset = json.load(f)
    with open(ally_json_path, "r", encoding="utf-8") as f:
        ally_data = json.load(f)

    if data_dir is None:
        data_dir = os.path.dirname(os.path.abspath(ally_json_path))

    mgr = CharacterInstanceManager()
    op = BattleOpStateManager()

    enemy_slots = {int(k): v for k, v in preset["enemy_slots"].items()}
    ally_slots = {int(k): v for k, v in preset["ally_slots"].items()}

    enabled_allies = [pos for pos, cfg in ally_slots.items() if cfg.get("enabled")]
    if not enabled_allies:
        raise RuntimeError("preset 中没有 enabled ally")
    attacker_pos = enabled_allies[0]
    attacker_cfg = ally_slots[attacker_pos]
    target_enemy_pos = int(attacker_cfg.get("target_enemy_pos", 0))

    for enemy_pos in (0, 1, 2):
        apply_enemy_slot(mgr, enemy_pos, enemy_slots.get(enemy_pos, {}), data_dir=data_dir)
    for ally_pos in (0, 1, 2):
        cfg = ally_slots.get(ally_pos, {})
        if ally_pos == attacker_pos:
            apply_ally_slot(mgr, ally_pos, cfg, ally_data)
        elif cfg.get("enabled"):
            other_path = os.path.join(data_dir, f"{int(cfg['character_id'])}.json")
            with open(other_path, "r", encoding="utf-8") as f:
                other_data = json.load(f)
            apply_ally_slot(mgr, ally_pos, cfg, other_data)

    skill_order: List[List[int]] = []
    for ally_pos in enabled_allies:
        cfg = ally_slots[ally_pos]
        op.set_enemy_target_pos(ally_pos, int(cfg.get("target_enemy_pos", 0)))
        txt = str(cfg.get("skill_order_text", "")).strip()
        nums = [int(x.strip()) for x in txt.split(",") if x.strip()] if txt else [0, 1, 2]
        skill_order.extend([[ally_pos, n] for n in nums])
        op.set_shield_open_count(ally_pos, int(cfg.get("shield_open_count", 0)))
        op.set_attack_params(ally_pos, str(cfg.get("attack_type", "5")), int(cfg.get("spirit_level", 0)))
    op.set_skill_order(skill_order)

    ally_front_chars = [mgr.get_character_instance("我方前排", i) for i in (0, 1, 2)]
    enemy_chars = [mgr.get_character_instance("敌方", i) for i in (0, 1, 2)]
    op_result = {
        "success": True,
        "errors": [],
        "skill_execution": [],
        "shield_execution": [],
        "spirit_execution": [],
        "pre_attack_buff_execution": [],
        "post_attack_buff_execution": [],
    }

    debug: Dict[str, Any] = {
        "meta": {
            "preset_path": os.path.abspath(preset_path),
            "ally_json_path": os.path.abspath(ally_json_path),
            "attacker_pos": attacker_pos,
            "target_enemy_pos": target_enemy_pos,
            "attack_type": attacker_cfg.get("attack_type"),
            "spirit_level": attacker_cfg.get("spirit_level"),
            "skill_order": skill_order,
        },
        "phases": {},
    }

    debug["phases"]["phase0_init"] = snapshot_world(mgr, attacker_pos=attacker_pos, target_enemy_pos=target_enemy_pos)

    op._execute_skills(mgr, ally_front_chars, enemy_chars, op_result)
    skill_snaps = []
    for rec in op_result["skill_execution"]:
        if int(rec.get("char_pos_idx", -1)) == attacker_pos:
            skill_snaps.append({
                "record": _to_jsonable(rec),
                "snapshot": snapshot_world(mgr, attacker_pos=attacker_pos, target_enemy_pos=target_enemy_pos),
            })
    debug["phases"]["phase1_after_skills"] = skill_snaps

    op._execute_shields(mgr, ally_front_chars, op_result)
    debug["phases"]["phase2_after_shield"] = {
        "records": _to_jsonable(op_result["shield_execution"]),
        "snapshot": snapshot_world(mgr, attacker_pos=attacker_pos, target_enemy_pos=target_enemy_pos),
    }

    op._execute_spirit(mgr, ally_front_chars, op_result)
    debug["phases"]["phase3_after_spirit"] = {
        "records": _to_jsonable(op_result["spirit_execution"]),
        "snapshot": snapshot_world(mgr, attacker_pos=attacker_pos, target_enemy_pos=target_enemy_pos),
    }

    order, snapshot = get_ally_front_attack_order(mgr, return_debug=True)
    debug["phases"]["phase5_attack_order"] = {
        "order": list(order),
        "snapshot": _to_jsonable(snapshot),
    }

    op.execute_pre_attack_buffs_for_attacker(mgr, attacker_pos, op_result)
    debug["phases"]["phase4_pre_attack"] = {
        "records": _to_jsonable(op_result["pre_attack_buff_execution"]),
        "snapshot": snapshot_world(mgr, attacker_pos=attacker_pos, target_enemy_pos=target_enemy_pos),
    }

    attacker = mgr.get_character_instance("我方前排", attacker_pos)
    attack_type = op.get_op_status(attacker_pos).attack_type
    spirit_level = int(op.get_op_status(attacker_pos).spirit_level)
    attack_skill_data = attacker.attack_skills[attack_type]
    segment_order = parse_attack_segment_order(attack_skill_data, spirit_level)
    debug["phases"]["phase6_segment_order"] = {
        "segment_order": list(segment_order),
        "paragraph_executed_before": list(attacker.paragraph_executed),
    }

    details = execute_attack_phase_for_attacker(
        mgr,
        op,
        attacker_pos=attacker_pos,
        segment_order=segment_order,
        debug_print=False,
    )

    phase67 = []
    for idx, d in enumerate(details):
        dbg = d.get("debug", {}) or {}
        phase67.append({
            "detail_index": idx,
            "i": dbg.get("i"),
            "seg": d.get("seg"),
            "enemy_pos": d.get("enemy_pos"),
            "first": dbg.get("first"),
            "paragraph_buff_result": dbg.get("paragraph_buff_result"),
            "effects_1": dbg.get("effects_1", []),
            "effects_2": dbg.get("effects_2", []),
            "effects_2_skipped": dbg.get("effects_2_skipped", []),
            "flags": d.get("flags", {}),
            "unhandled_effects": d.get("unhandled_effects", []),
        })
    debug["phases"]["phase7_segment_gate_and_effects"] = phase67
    debug["phases"]["phase8_shot_details"] = details

    op.execute_post_attack_buffs_for_attacker(mgr, attacker_pos, op_result)
    debug["phases"]["phase9_post_attack"] = {
        "records": _to_jsonable(op_result["post_attack_buff_execution"]),
        "snapshot": snapshot_world(mgr, attacker_pos=attacker_pos, target_enemy_pos=target_enemy_pos),
    }

    seg_damage = {f"seg{i}": 0 for i in range(6)}
    enemy_totals = {0: 0, 1: 0, 2: 0}
    total_damage = 0
    for d in details:
        dmg = int(d.get("damage_int", 0) or 0)
        seg = int(d.get("seg", -1))
        ep = int(d.get("enemy_pos", -1))
        if 0 <= seg < 6:
            seg_damage[f"seg{seg}"] += dmg
        if ep in enemy_totals:
            enemy_totals[ep] += dmg
        total_damage += dmg

    debug["summary"] = {
        "seg_damage": seg_damage,
        "enemy_totals": enemy_totals,
        "total_damage": total_damage,
        "op_errors": list(op_result.get("errors", [])),
    }
    debug["op_result"] = _to_jsonable(op_result)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(debug, f, ensure_ascii=False, indent=2)

    return debug


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="./presets/uuz.json")
    ap.add_argument("--ally", default="./datajson/5010.json")
    ap.add_argument("--data_dir", default="./datajson")
    ap.add_argument("--out", default="./debug_7085_uuz.json")
    args = ap.parse_args()

    result = run_debug(args.preset, args.ally, data_dir=args.data_dir, out_path=args.out)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"written: {args.out}")
