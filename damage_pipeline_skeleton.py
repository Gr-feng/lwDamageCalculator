"""单文件：段落首发 gate + 段落内 buff + effect(两阶段) + 单发伤害（v3：接入“基本伤害”公式）

v3 更新重点（基于你最新说明）：
- 从 attacks[seg] 读取：yinyang / damage(威力) / acc / cri / element / killers / type
- 从 global_attributes 读取：target（取第 0 位）/ damage_extend（取第 5 位）
- 目标 target==2（敌方全体）：
  - 首发判定为 True 时：段落内 buff 只执行一次；effects_1（12~16）对“当前存在的每个敌方”都执行一次
  - 每一发伤害：对每个敌方各算一次（忽略 amt，多目标只做“每敌方一发”）

实现范围（先跑通公式主干，补正分阶段接入）：
- ✅ 基本伤害：
  基本伤害 = 我方攻击 / 敌方防御 × 威力 × 角色等级补正 × 弹幕等级补正
  - 随机数=1
  - 绘卷补正=1（TODO）
- ✅ 我方攻击：
  atk = 面板攻×攻buff + 面板防×防buff×硬质系数 + 面板速×速buff×斩裂系数
  - 硬质系数（effect4）与斩裂系数（effect5）先按 effect flag 接入
- ✅ 敌方防御：
  def = 面板防×防buff
  - effect2(pierce_def_buffs)=True 时：忽略防御 buff（只用面板防）
- ✅ 面板衰减：
  - 阳攻/阳防受毒雾(type=4)
  - 阴攻/阴防受燃烧(type=1)
  - 速度受冰冻(type=2)
  面板_final = 面板_base × 0.875^层数
- ✅ buff 计算（仅 id=1 & id=41）：
  - sub 1/2/3/4/5/8/9：倍率 1+0.3*n 或 1/(1+0.3*abs(n))
  - sub 6/7/10/11：倍率 0.2*n 或 1/(0.2*abs(n))
  - 一阶与二阶分别算后相乘

暴击/特攻/属性克制等额外补正：
- 先只实现“是否暴击”判定（killer 必暴击；否则按 cri%×会心命中 buff）与 “暴击&特攻补正”乘区（TODO：你后续还会补全）。

⚠️ 注意：这里仍保持可 smoke：不引入随机；命中暂时默认命中（但会算 hit_rate 写入 detail 便于核对）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from character import CharacterInstanceManager, CharacterInstance
from battle_op_state import BattleOpStateManager
from buff_effect import parse_buff, parse_effect


# ============================================================
# 数据结构
# ============================================================

@dataclass(frozen=True)
class ShotContext:
    attack_type: str
    spirit_level: int
    seg: int  # 0..5，与 attacks[seg] 对齐

    # 来自 global_attributes
    target_mode: int  # 1=单体 2=全体（取 target[0]）
    danmaku_extend_pct: float  # damage_extend[5]，例如 128 => 1.28

    # attack entry
    attack_entry: Dict[str, Any]


@dataclass
class DamageContext:
    attacker_pos: int
    enemy_pos: int
    attack_type: str
    spirit_level: int
    seg: int

    flags: Dict[str, Any] = field(default_factory=dict)          # effect2 写入
    runtime_overrides: Dict[str, Any] = field(default_factory=dict)

    # debug
    unhandled_effects: List[Tuple[int, int]] = field(default_factory=list)


# ============================================================
# Gate / reset
# ============================================================

def first_launch_and_mark(attacker: CharacterInstance, seg: int) -> bool:
    if seg < 0 or seg >= 6:
        raise ValueError(f"seg 必须是 0~5，当前={seg}")
    if attacker.get_paragraph_executed(seg):
        return False
    attacker.set_paragraph_executed(seg)
    return True


def reset_paragraph_executed(attacker: CharacterInstance) -> None:
    attacker.set_paragraph_executed(6)


# ============================================================
# Shot ctx
# ============================================================

def _get_attack_skill_data(attacker: CharacterInstance, attack_type: str) -> Dict[str, Any]:
    if attack_type not in attacker.attack_skills:
        raise KeyError(f"attack_type={attack_type} not found")
    return attacker.attack_skills[attack_type]


def _get_target_mode(attack_skill_data: Dict[str, Any]) -> int:
    ga = attack_skill_data.get("global_attributes", {}) or {}
    t = ga.get("target", [1])
    if not isinstance(t, list) or not t:
        return 1
    return int(t[0])


def _get_danmaku_extend_pct(attack_skill_data: Dict[str, Any]) -> float:
    ga = attack_skill_data.get("global_attributes", {}) or {}
    de = ga.get("damage_extend", [])
    if isinstance(de, list) and len(de) >= 6:
        return float(de[5]) / 100.0
    return 1.0


def build_shot_ctx(mgr: CharacterInstanceManager, op: BattleOpStateManager, attacker_pos: int, *, seg: int) -> ShotContext:
    attacker = mgr.get_character_instance("我方前排", attacker_pos)
    if attacker is None:
        raise ValueError(f"attacker 不存在 pos={attacker_pos}")

    op_status = op.get_op_status(attacker_pos)
    attack_type = op_status.attack_type
    spirit_level = int(getattr(op_status, "spirit_level", 0))

    attack_skill_data = _get_attack_skill_data(attacker, attack_type)
    attacks = attack_skill_data.get("attacks", [])
    if not isinstance(attacks, list) or not attacks:
        raise ValueError("attack_skill_data['attacks'] 为空")
    if seg < 0 or seg >= len(attacks):
        raise IndexError(f"seg={seg} 超出范围 len(attacks)={len(attacks)}")

    return ShotContext(
        attack_type=attack_type,
        spirit_level=spirit_level,
        seg=seg,
        target_mode=_get_target_mode(attack_skill_data),
        danmaku_extend_pct=_get_danmaku_extend_pct(attack_skill_data),
        attack_entry=attacks[seg],
    )


# ============================================================
# 段落 payload：buff/effect parse
# ============================================================

def extract_paragraph_payload(attack_entry: Dict[str, Any]) -> Tuple[List[List[int]], List[List[int]]]:
    buff_arr = attack_entry.get("buff", []) or []
    effect_arr = attack_entry.get("effect", []) or []

    paragraph_buffs = parse_buff(buff_arr) if buff_arr else []
    effects = parse_effect(effect_arr) if effect_arr else []

    return paragraph_buffs, effects


# ============================================================
# Effect 两阶段
# ============================================================

KNOWN_EFFECT_IDS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}
EXECUTED_EFFECT2_IDS = {1, 2, 3, 4, 5}


def _attacker_id_str(attacker: CharacterInstance) -> str:
    info = getattr(attacker, "character_info", {}) or {}
    cid = info.get("id", info.get("character_id", ""))
    name = info.get("name", "")
    if cid or name:
        return f"id={cid} name={name}".strip()
    return f"CharacterInstance@{id(attacker)}"


def split_effects(effects: List[List[int]]) -> Tuple[List[List[int]], List[List[int]]]:
    e1: List[List[int]] = []
    e2: List[List[int]] = []
    for pair in effects:
        if not pair or len(pair) < 2:
            continue

        effect_id, value = int(pair[0]), int(pair[1])

        # 0,0 视为空效果/占位
        if effect_id == 0:
            continue

        if 12 <= effect_id <= 16:
            e1.append([effect_id, value])
        else:
            e2.append([effect_id, value])
    return e1, e2

def apply_effects_1_once_for_defender(
    mgr: CharacterInstanceManager,
    enemy_pos: int,
    effects_1: List[List[int]],
    *,
    log: Optional[Dict[str, Any]] = None,
) -> None:
    """effects_1：只在 first_launch=True 时执行一次；对指定敌方执行。

    12~16：击破敌方对应异常类型结界（type = effect_id - 11）
    """
    if not effects_1:
        return

    defender = mgr.get_character_instance("敌方", enemy_pos)
    if defender is None:
        return

    for effect_id, value in effects_1:
        if 12 <= effect_id <= 16:
            barrier_type = effect_id - 11
            broken = defender.break_barrier(barrier_type)
            if log is not None:
                log.setdefault("effects_1", []).append({"enemy_pos": enemy_pos, "effect_id": effect_id, "value": value, "broken": broken})


def apply_effects_2_per_hit(
    mgr: CharacterInstanceManager,
    attacker_pos: int,
    effects_2: List[List[int]],
    ctx: DamageContext,
    *,
    log: Optional[Dict[str, Any]] = None,
) -> None:
    if not effects_2:
        return

    attacker = mgr.get_character_instance("我方前排", attacker_pos)
    if attacker is None:
        raise ValueError(f"attacker 不存在 pos={attacker_pos}")

    for effect_id, value in effects_2:
        effect_id = int(effect_id)
        value = int(value)

        # 0,0 视为空效果/占位效果，直接跳过
        if effect_id == 0:
            if log is not None:
                log.setdefault("effects_2_skipped_zero", []).append(
                    {"effect_id": effect_id, "value": value}
                )
            continue

        # 未知 effect：报错
        if effect_id not in KNOWN_EFFECT_IDS:
            who = _attacker_id_str(attacker)
            raise ValueError(f"未知 effect_id={effect_id}, value={value}（发生于攻击者 {who}）")

        # 已知但当前不执行：记录并跳过
        if effect_id not in EXECUTED_EFFECT2_IDS:
            ctx.unhandled_effects.append((effect_id, value))
            if log is not None:
                log.setdefault("effects_2_skipped", []).append(
                    {"effect_id": effect_id, "value": value}
                )
            continue

        if effect_id == 1:
            ctx.flags["guaranteed_hit"] = True

        elif effect_id == 2:
            # 忽略敌方防御 buff/debuff 变动部分，只对基础防御
            ctx.flags["pierce_def_buffs"] = True

        elif effect_id == 3:
            # value=1 -> 强制按阳防
            # value=2 -> 强制按阴防
            if value == 1:
                ctx.flags["force_def_type"] = "yang"
            elif value == 2:
                ctx.flags["force_def_type"] = "yin"
            else:
                ctx.unhandled_effects.append((effect_id, value))
                if log is not None:
                    log.setdefault("effects_2_skipped", []).append({"effect_id": effect_id, "value": value})

        elif effect_id == 4:
            ctx.flags["def_to_atk_pct"] = value

        elif effect_id == 5:
            ctx.flags["spd_to_atk_pct"] = value
            
        if log is not None:
            log.setdefault("effects_2", []).append({"effect_id": effect_id, "value": value})

# ============================================================
# Buff 计算（只做 id=1 & 41）
# ============================================================

# sub_id 分类：
# - 0.3 系（面板类 + CRI攻/防）：1,2,3,4,5,8,9
# - 0.2 系（命中/回避 + CRI命中/回避）：6,7,10,11
SUB_03 = {1, 2, 3, 4, 5, 8, 9}
SUB_02 = {6, 7, 10, 11}


def _clamp_layers(x: float, limit: int = 10) -> int:
    if x > limit:
        return limit
    if x < -limit:
        return -limit
    return int(x)


def _layers_from_buffs(buffs: List[Any], buff_id: int, sub_id: int) -> int:
    s = 0.0
    for b in buffs:
        if int(getattr(b, "buff_id", -1)) == buff_id and int(getattr(b, "sub_id", -1)) == sub_id:
            s += float(getattr(b, "value", 0.0))
    return _clamp_layers(s)


def _mult_from_layers(sub_id: int, layers: int) -> float:
    if layers == 0:
        # 对 0.2 系，0 层时乘数应视为 1
        return 1.0

    if sub_id in SUB_03:
        if layers > 0:
            return 1.0 + 0.3 * layers
        return 1.0 / (1.0 + 0.3 * abs(layers))

    if sub_id in SUB_02:
        if layers > 0:
            return 0.2 * layers
        return 1.0 / (0.2 * abs(layers))

    # TODO：其它 sub_id
    return 1.0


def get_buff_multiplier(char: CharacterInstance, sub_id: int) -> float:
    """取最终 buff 倍率（只考虑 id=1 与 id=41）。"""
    buffs = list(getattr(char, "buffs", []) or [])

    l1 = _layers_from_buffs(buffs, 1, sub_id)
    l2 = _layers_from_buffs(buffs, 41, sub_id)

    m1 = _mult_from_layers(sub_id, l1)
    m2 = _mult_from_layers(sub_id, l2)
    return float(m1) * float(m2)


def get_crit_attack_multiplier(attacker: CharacterInstance, defender: CharacterInstance) -> float:
    """暴击&特攻补正：1 + 会心攻击buff（层差：我方sub8 - 对方sub9）。"""
    buffs_a = list(getattr(attacker, "buffs", []) or [])
    buffs_d = list(getattr(defender, "buffs", []) or [])

    la = _layers_from_buffs(buffs_a, 1, 8) + _layers_from_buffs(buffs_a, 41, 8)
    ld = _layers_from_buffs(buffs_d, 1, 9) + _layers_from_buffs(buffs_d, 41, 9)

    # 层差（下降取负），再 clamp
    diff = _clamp_layers(la - ld)

    # 用 0.3 系转换成倍率，但这里是“加成项”：1 + buff_value
    # buff_value 本体用常规 0.3 系（上升：0.3*n；下降：-(1 - 1/(1+0.3*|n|)) 这种更精确）
    # 目前先按你给的近似：上升用 0.3*n；下降用 - (1 - 1/(1+0.3*|n|))
    if diff == 0:
        return 1.0
    if diff > 0:
        return 1.0 + 0.3 * diff
    # 下降：等价于乘以 (1/(1+0.3*|n|))，但你这里写的是“1 + 会心攻击buff”，所以要转成加成项。
    # 简化：把会心攻击buff视为 (1/(1+0.3*|n|))，则整体=1+that，会偏大。
    # 更合理：把“buff_value”当作负增益：-0.3*|n| 的近似。
    return max(0.0, 1.0 - 0.3 * abs(diff))


def get_crit_hit_multiplier(attacker: CharacterInstance, defender: CharacterInstance) -> float:
    """会心命中 buff：层差（我方sub10 - 对方sub11），使用 0.2 系。"""
    buffs_a = list(getattr(attacker, "buffs", []) or [])
    buffs_d = list(getattr(defender, "buffs", []) or [])

    la = _layers_from_buffs(buffs_a, 1, 10) + _layers_from_buffs(buffs_a, 41, 10)
    ld = _layers_from_buffs(buffs_d, 1, 11) + _layers_from_buffs(buffs_d, 41, 11)

    diff = _clamp_layers(la - ld)
    return _mult_from_layers(10, diff)

def _sub02_expected_mult_from_diff(diff: int) -> float:
    """0.2 系层差 -> 乘区
    你最新口径：
    - diff >= 0: 1 + 0.2 * diff
    - diff < 0 : 1 / (1 + 0.2 * abs(diff))
    """
    diff = _clamp_layers(diff)
    if diff >= 0:
        return 1.0 + 0.2 * diff
    return 1.0 / (1.0 + 0.2 * abs(diff))


def _get_layer_diff(attacker: CharacterInstance, defender: CharacterInstance, sub_attacker: int, sub_defender: int) -> int:
    """取层差：我方层数 - 对方层数，并 clamp 到 [-10, 10]。"""
    buffs_a = list(getattr(attacker, "buffs", []) or [])
    buffs_d = list(getattr(defender, "buffs", []) or [])

    la = _layers_from_buffs(buffs_a, 1, sub_attacker) + _layers_from_buffs(buffs_a, 41, sub_attacker)
    ld = _layers_from_buffs(buffs_d, 1, sub_defender) + _layers_from_buffs(buffs_d, 41, sub_defender)

    return _clamp_layers(la - ld)

def _get_hit_correction(attacker: CharacterInstance, defender: CharacterInstance, attack_entry: Dict[str, Any], ctx: DamageContext) -> Dict[str, Any]:
    """命中率补正（作为最终伤害乘区，不做随机命中判定）"""
    acc = float(attack_entry.get("acc", 100.0)) / 100.0

    if bool(ctx.flags.get("guaranteed_hit", False)):
        return {
            "acc": acc,
            "hit_diff": None,
            "hit_mult": 1.0,
            "hit_correction": 1.0,
            "guaranteed_hit": True,
        }

    # 命中 sub6，对方回避 sub7
    diff = _get_layer_diff(attacker, defender, 6, 7)
    hit_mult = _sub02_expected_mult_from_diff(diff)
    hit_correction = acc * hit_mult

    return {
        "acc": acc,
        "hit_diff": diff,
        "hit_mult": hit_mult,
        "hit_correction": hit_correction,
        "guaranteed_hit": False,
    }


def _get_crit_expectation(mgr: CharacterInstanceManager, attacker: CharacterInstance, defender: CharacterInstance, attack_entry: Dict[str, Any]) -> Dict[str, Any]:
    cri = float(attack_entry.get("cri", 0.0)) / 100.0
    killer = _killer_triggers(attack_entry, defender)

    buff47 = _get_buff47_frontline_effects(mgr, attacker)

    # 47,9：会心率上升，加算到基础 cri
    cri_base = cri + float(buff47["crit_rate_bonus"])

    # 会心命中层差：我方 sub10 - 对方 sub11
    crit_hit_diff = _get_layer_diff(attacker, defender, 10, 11)
    crit_hit_mult = _sub02_expected_mult_from_diff(crit_hit_diff)

    # 会心率
    crit_rate = 1.0 if killer else (cri_base * crit_hit_mult)

    buffs_a = list(getattr(attacker, "buffs", []) or [])
    buffs_d = list(getattr(defender, "buffs", []) or [])

    crit_atk_l1 = _clamp_layers(
        _layers_from_buffs(buffs_a, 1, 8) - _layers_from_buffs(buffs_d, 1, 9)
    )
    crit_atk_l2 = _clamp_layers(
        _layers_from_buffs(buffs_a, 41, 8) - _layers_from_buffs(buffs_d, 41, 9)
    )

    crit_atk_mult_1 = _mult_from_layers(8, crit_atk_l1)
    crit_atk_mult_2 = _mult_from_layers(8, crit_atk_l2)

    # 原始暴击伤害倍率
    crit_bonus = crit_atk_mult_1 * crit_atk_mult_2

    # 47,8：cri伤害上升，作为独立倍率乘在 crit_bonus 上
    crit_damage_corr_47 = float(buff47["crit_damage_correction"])
    crit_bonus *= crit_damage_corr_47

    if killer:
        crit_correction = 1.0 + crit_bonus
        crit_mode = "killer"
    else:
        crit_correction = 1.0 + crit_rate * crit_bonus
        crit_mode = "normal"

    return {
        "cri": cri,
        "cri_base_after_47_9": cri_base,
        "killer": killer,
        "crit_mode": crit_mode,
        "crit_hit_diff": crit_hit_diff,
        "crit_hit_mult": crit_hit_mult,
        "crit_rate": crit_rate,
        "crit_atk_l1": crit_atk_l1,
        "crit_atk_l2": crit_atk_l2,
        "crit_atk_mult_1": crit_atk_mult_1,
        "crit_atk_mult_2": crit_atk_mult_2,
        "crit_damage_correction_47_8": crit_damage_corr_47,
        "crit_bonus": crit_bonus,
        "crit_correction": crit_correction,
    }

def _get_stats_pct(char: CharacterInstance, key: str) -> float:
    stats = getattr(char, "stats", None)
    return float(getattr(stats, key, 0.0)) / 100.0

def _get_skill_element_attack_bonus(attacker: CharacterInstance, element: int) -> float:
    """
    技能属性增伤：
    - buff_id == 16
    - sub_id == element
    value=35 -> 0.35

    如果你后续确认 sub_id 映射不是直接等于 element，再改这里。
    """
    total = 0.0
    for b in list(getattr(attacker, "buffs", []) or []):
        if int(getattr(b, "buff_id", -1)) == 16 and int(getattr(b, "sub_id", -1)) == element:
            total += float(getattr(b, "value", 0.0)) / 100.0
    return total

def _get_skill_element_resist_bonus(defender: CharacterInstance, element: int) -> float:
    """
    技能属性减伤：
    - buff_id == 13
    - sub_id == element
    value=20 -> 0.20
    """
    total = 0.0
    for b in list(getattr(defender, "buffs", []) or []):
        if int(getattr(b, "buff_id", -1)) == 13 and int(getattr(b, "sub_id", -1)) == element:
            total += float(getattr(b, "value", 0.0)) / 100.0
    return total

def _get_adv_disadv_buff_bonus(char: CharacterInstance, buff_id: int, sub_id: int) -> float:
    """
    通用读取：
    - buff_id=49: 属性增伤
    - buff_id=50: 属性减伤
    - sub_id=1: 有利属性
    - sub_id=2: 不利属性

    value=20 -> 0.20
    """
    total = 0.0
    for b in list(getattr(char, "buffs", []) or []):
        if int(getattr(b, "buff_id", -1)) == buff_id and int(getattr(b, "sub_id", -1)) == sub_id:
            total += float(getattr(b, "value", 0.0)) / 100.0
    return total

def _get_element_correction(attacker: CharacterInstance, defender: CharacterInstance, attack_entry: Dict[str, Any]) -> Dict[str, Any]:
    element = int(attack_entry.get("element", 0))

    defender_stats = getattr(defender, "stats", None)
    quality = list(getattr(defender_stats, "quality", []) or [])

    if element < 0 or element >= len(quality):
        return {
            "element": element,
            "quality_value": None,
            "element_mode": "none",
            "element_correction": 1.0,
        }

    qv = int(quality[element])

    # 能力属性增伤/减伤（来自 stats）
    adv_atk = _get_stats_pct(attacker, "advantage_attack")
    dis_atk = _get_stats_pct(attacker, "disadvantage_attack")
    adv_res = _get_stats_pct(defender, "advantage_resist")
    dis_res = _get_stats_pct(defender, "disadvantage_resist")

    # 技能元素增伤/减伤（与有利不利无关，只看当前 element）
    skill_atk = _get_skill_element_attack_bonus(attacker, element)   # buff_id=16
    skill_res = _get_skill_element_resist_bonus(defender, element)   # buff_id=13

    # 49/50：有利/不利属性增减伤
    adv_bonus = _get_adv_disadv_buff_bonus(attacker, 49, 1)   # 我方有利属性增伤
    adv_penalty = _get_adv_disadv_buff_bonus(defender, 50, 1) # 对方有利属性减伤

    dis_bonus = _get_adv_disadv_buff_bonus(attacker, 49, 2)   # 我方不利属性增伤
    dis_penalty = _get_adv_disadv_buff_bonus(defender, 50, 2) # 对方不利属性减伤

    if qv == 0:
        # 弱点
        correction = 2.0 * (
            1.0
            + adv_atk
            + skill_atk
            - adv_res
            - skill_res
            + adv_bonus
            - adv_penalty
        )
        mode = "advantage"

    elif qv == 2:
        # 抵抗
        correction = 0.5 * (
            1.0
            + dis_atk
            + skill_atk
            - dis_res
            - skill_res
            + dis_bonus
            - dis_penalty
        )
        mode = "disadvantage"

    else:
        # 普通
        correction = 1.0 + skill_atk - skill_res
        mode = "normal"

    if correction < 0:
        correction = 0.0

    return {
        "element": element,
        "quality_value": qv,
        "element_mode": mode,

        "advantage_attack": adv_atk,
        "disadvantage_attack": dis_atk,
        "advantage_resist": adv_res,
        "disadvantage_resist": dis_res,

        "skill_element_attack": skill_atk,
        "skill_element_resist": skill_res,

        "adv_bonus_49_1": adv_bonus,
        "adv_penalty_50_1": adv_penalty,
        "dis_bonus_49_2": dis_bonus,
        "dis_penalty_50_2": dis_penalty,

        "element_correction": correction,
    }

def _get_bullet_type_correction(attacker: CharacterInstance, defender: CharacterInstance, attack_entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    弹种增伤/减伤独立乘区：
    - buff_id=15: 弹种增伤
    - buff_id=12: 弹种减伤
    - sub_id == 当前 attack_entry["type"]

    公式：
        1 + 增伤 - 减伤
    """
    bullet_type = int(attack_entry.get("type", 0))

    atk_bonus = 0.0
    for b in list(getattr(attacker, "buffs", []) or []):
        if int(getattr(b, "buff_id", -1)) == 15 and int(getattr(b, "sub_id", -1)) == bullet_type:
            atk_bonus += float(getattr(b, "value", 0.0)) / 100.0

    res_bonus = 0.0
    for b in list(getattr(defender, "buffs", []) or []):
        if int(getattr(b, "buff_id", -1)) == 12 and int(getattr(b, "sub_id", -1)) == bullet_type:
            res_bonus += float(getattr(b, "value", 0.0)) / 100.0

    correction = 1.0 + atk_bonus - res_bonus
    if correction < 0:
        correction = 0.0

    return {
        "bullet_type": bullet_type,
        "bullet_type_attack_bonus": atk_bonus,
        "bullet_type_resist_bonus": res_bonus,
        "bullet_type_correction": correction,
    }

def _count_alive_frontline_allies(mgr: CharacterInstanceManager) -> int:
    """统计当前存活的我方前排人数（pos 0/1/2，hp>0）。"""
    cnt = 0
    for pos in (0, 1, 2):
        c = mgr.get_character_instance("我方前排", pos)
        if c is not None and getattr(c.stats, "hp", 0) > 0:
            cnt += 1
    return cnt


def _sum_buff_pct(char: CharacterInstance, buff_id: int, sub_id: int) -> float:
    """把指定 buff 的 value 累加成百分比小数。value=20 -> 0.20"""
    total = 0.0
    for b in list(getattr(char, "buffs", []) or []):
        if int(getattr(b, "buff_id", -1)) == buff_id and int(getattr(b, "sub_id", -1)) == sub_id:
            total += float(getattr(b, "value", 0.0)) / 100.0
    return total

def _get_buff47_frontline_effects(mgr: CharacterInstanceManager, attacker: CharacterInstance) -> Dict[str, float]:
    """
    buff_id=47：
    - sub5: 速度上升（作用在速度项）
    - sub7: 攻击伤害上升（独立乘区）
    - sub8: cri伤害上升（作用在 crit_bonus）
    - sub9: cri命中率上升（加算到基础 cri）
    """
    frontline_cnt = _count_alive_frontline_allies(mgr)

    spd_bonus = _sum_buff_pct(attacker, 47, 5) * frontline_cnt
    dmg_bonus = _sum_buff_pct(attacker, 47, 7) * frontline_cnt
    crit_dmg_bonus = _sum_buff_pct(attacker, 47, 8) * frontline_cnt
    crit_rate_bonus = _sum_buff_pct(attacker, 47, 9) * frontline_cnt

    return {
        "frontline_cnt": frontline_cnt,
        "spd_correction": 1.0 + spd_bonus,
        "damage_correction": 1.0 + dmg_bonus,
        "crit_damage_correction": 1.0 + crit_dmg_bonus,
        "crit_rate_bonus": crit_rate_bonus,  # 这是加算，不是乘算
    }

def _get_buff48_correction(attacker: CharacterInstance, ctx: DamageContext) -> Dict[str, Any]:
    """
    buff_id=48：
    - sub1: 血量增伤（简化：1 + value）
    - sub2: 结界增伤（按进入攻击阶段前的结界存有量）
    - sub3: 灵力增伤（按进入攻击阶段前的灵力存有量，上限 5）

    三者独立，最后相乘。
    """
    hp_bonus_pct = _sum_buff_pct(attacker, 48, 1)
    barrier_bonus_pct = _sum_buff_pct(attacker, 48, 2)
    spirit_bonus_pct = _sum_buff_pct(attacker, 48, 3)

    # 48,1：血量增伤（你当前口径：不看实际血量，直接 1+value）
    hp_corr = 1.0 + hp_bonus_pct

    # 48,2：结界增伤 —— 用 shield 阶段前快照
    barrier_stock = int(ctx.runtime_overrides.get("barrier_stock_before_attack", 0))
    if barrier_stock < 0:
        barrier_stock = 0
    barrier_corr = 1.0 + barrier_bonus_pct * barrier_stock

    # 48,3：灵力增伤 —— 用 spirit 阶段前快照
    spirit_stock = float(ctx.runtime_overrides.get("spirit_stock_before_attack", 0.0))
    spirit_stock = min(5.0, max(0.0, spirit_stock))
    spirit_corr = 1.0 + spirit_bonus_pct * spirit_stock

    total = hp_corr * barrier_corr * spirit_corr

    return {
        "hp_bonus_pct": hp_bonus_pct,
        "barrier_bonus_pct": barrier_bonus_pct,
        "spirit_bonus_pct": spirit_bonus_pct,
        "barrier_stock": barrier_stock,
        "spirit_stock": spirit_stock,
        "hp_correction": hp_corr,
        "barrier_correction": barrier_corr,
        "spirit_correction": spirit_corr,
        "buff48_correction": total,
    }

def _get_buff54_value(char: CharacterInstance, sub_id: int) -> float:
    """
    TODO:
    buff_id=54 实际更接近“场地 buff / 全局效果”，
    当前在伤害计算阶段采用“挂在角色身上并等价读取”的近似实现。

    读取 buff_id=54 的指定 sub_id 数值，返回百分比小数。
    例如 value=30 -> 0.30

    由于 add_character_buff 已保证 54 互斥，
    理论上同一角色同一时刻只会有一个 54。
    """
    for b in list(getattr(char, "buffs", []) or []):
        if int(getattr(b, "buff_id", -1)) == 54 and int(getattr(b, "sub_id", -1)) == sub_id:
            return float(getattr(b, "value", 0.0)) / 100.0
    return 0.0

def _get_buff54_damage_correction(char: CharacterInstance) -> float:
    """
    54,703901：伤害增加，独立乘区
    value=30 -> 1.30
    """
    return 1.0 + _get_buff54_value(char, 703901)

def _get_buff580_flat_bonus(char: CharacterInstance, sub_id: int) -> float:
    """
    buff_id=580：固定面板加值
    sub_id:
      1=阳攻 2=阳防 3=阴攻 4=阴防 5=速度
    多条时直接累加。
    """
    total = 0.0
    for b in list(getattr(char, "buffs", []) or []):
        if int(getattr(b, "buff_id", -1)) == 580 and int(getattr(b, "sub_id", -1)) == sub_id:
            total += float(getattr(b, "value", 0.0))
    return total

# ============================================================
# 面板衰减（结界异常）
# ============================================================

# barrier.type：1燃烧 2冻结 3感电 4毒雾 5黑暗

def _count_active_barrier_type(char: CharacterInstance, barrier_type: int) -> int:
    bars = list(getattr(char, "barriers", []) or [])
    c = 0
    for b in bars:
        if getattr(b, "is_active", False) and int(getattr(b, "type", 0)) == barrier_type:
            c += 1
    return c


def _panel_decay(panel: float, stacks: int) -> float:
    if stacks <= 0:
        return float(panel)
    return float(panel) * (0.875 ** stacks)


# ============================================================
# 伤害计算（基本伤害 + 部分补正）
# ============================================================

def _get_level_multiplier(attacker: CharacterInstance) -> float:
    """角色等级补正：
    - re=False -> 100
    - re=True  -> 140

    注意：这里不是 1.0 / 1.4，而是直接乘 100 / 140。
    """
    info = getattr(attacker, "character_info", {}) or {}
    re = info.get("re", False)

    # 兼容 "True"/"False" 字符串
    if isinstance(re, str):
        re = (re.lower() == "true")

    return 140.0 if re else 100.0


def _choose_def_type(attack_entry: Dict[str, Any], ctx: DamageContext) -> str:
    """决定使用阳防/阴防：
    - effect30/31 强制
    - 否则按 yinyang：1阳 0阴
    """
    forced = ctx.flags.get("force_def_type")
    if forced in ("yang", "yin"):
        return forced

    yinyang = int(attack_entry.get("yinyang", 1))
    return "yang" if yinyang == 1 else "yin"


def _get_attack_panels(attacker: CharacterInstance, def_type: str) -> Tuple[float, float, float]:
    """返回（atk_panel, def_panel, spd_panel）并做异常衰减。

    阳系面板受毒雾(type=4)；阴系面板受燃烧(type=1)；速度受冰冻(type=2)
    """
    s = attacker.stats

    spd_stacks = _count_active_barrier_type(attacker, 2)
    spd_panel = _panel_decay(float(s.spd), spd_stacks)

    if def_type == "yang":
        stacks = _count_active_barrier_type(attacker, 4)
        atk_panel = _panel_decay(float(s.yang_atk), stacks)
        def_panel = _panel_decay(float(s.yang_def), stacks)
    else:
        stacks = _count_active_barrier_type(attacker, 1)
        atk_panel = _panel_decay(float(s.yin_atk), stacks)
        def_panel = _panel_decay(float(s.yin_def), stacks)

    return atk_panel, def_panel, spd_panel


def _get_def_panels(defender: CharacterInstance, def_type: str) -> float:
    """返回 defender 防御面板（已做异常衰减）。"""
    s = defender.stats
    if def_type == "yang":
        stacks = _count_active_barrier_type(defender, 4)
        return _panel_decay(float(s.yang_def), stacks)
    else:
        stacks = _count_active_barrier_type(defender, 1)
        return _panel_decay(float(s.yin_def), stacks)

def _compute_base_atk(attacker, ctx, def_type):
    atk_panel, def_panel, spd_panel = _get_attack_panels(attacker, def_type)

    # 先把 580 固定加值加到面板上（在乘 buff 前）
    if def_type == "yang":
        atk_flat = _get_buff580_flat_bonus(attacker, 1)   # 阳攻
        def_flat = _get_buff580_flat_bonus(attacker, 2)   # 阳防
        atk_mult = get_buff_multiplier(attacker, 1)
        def_mult = get_buff_multiplier(attacker, 2)
    else:
        atk_flat = _get_buff580_flat_bonus(attacker, 3)   # 阴攻
        def_flat = _get_buff580_flat_bonus(attacker, 4)   # 阴防
        atk_mult = get_buff_multiplier(attacker, 3)
        def_mult = get_buff_multiplier(attacker, 4)

    spd_flat = _get_buff580_flat_bonus(attacker, 5)       # 速度
    spd_mult = get_buff_multiplier(attacker, 5)

    atk_panel_eff = atk_panel + atk_flat
    def_panel_eff = def_panel + def_flat
    spd_panel_eff = spd_panel + spd_flat

    # TODO:
    # buff_id=54 本质是场地/全局效果，这里先做“挂在 attacker 身上”的等价处理。
    buff54_yang_atk = _get_buff54_value(attacker, 703099)  # 阳攻上升 / 敌方阳攻下降
    buff54_yang_def = _get_buff54_value(attacker, 703801)  # 阳防上升 / 敌方阳防下降

    if def_type == "yang":
        atk_panel_eff *= (1.0 + buff54_yang_atk)
        def_panel_eff *= (1.0 + buff54_yang_def)

    hard = float(ctx.flags.get("def_to_atk_pct", 0.0)) / 100.0
    slash = float(ctx.flags.get("spd_to_atk_pct", 0.0)) / 100.0

    atk = (
        atk_panel_eff * atk_mult
        + def_panel_eff * def_mult * hard
        + spd_panel_eff * spd_mult * slash
    )

    return {
        "atk_panel": atk_panel,
        "def_panel": def_panel,
        "spd_panel": spd_panel,

        "atk_flat_580": atk_flat,
        "def_flat_580": def_flat,
        "spd_flat_580": spd_flat,

        "atk_panel_eff": atk_panel_eff,
        "def_panel_eff": def_panel_eff,
        "spd_panel_eff": spd_panel_eff,

        "buff54_yang_atk": buff54_yang_atk,
        "buff54_yang_def": buff54_yang_def,

        "atk_mult": atk_mult,
        "def_mult": def_mult,
        "spd_mult": spd_mult,

        "hard_pct": hard,
        "slash_pct": slash,
        "base_atk": atk,
    }

def _compute_base_def(attacker: CharacterInstance, defender: CharacterInstance, ctx: DamageContext, def_type: str) -> Dict[str, float]:
    def_panel = _get_def_panels(defender, def_type)

    # 580 固定加值也作用于防御面板
    if def_type == "yang":
        def_flat = _get_buff580_flat_bonus(defender, 2)   # 阳防
    else:
        def_flat = _get_buff580_flat_bonus(defender, 4)   # 阴防

    def_panel_eff = def_panel + def_flat

    # TODO:
    # buff_id=54 本质是场地/全局效果，这里先做“挂在 attacker 身上”的等价处理。
    # 703801：我方阳防上升，敌方阳防下降
    buff54_yang_def_from_attacker = _get_buff54_value(attacker, 703801)

    if def_type == "yang":
        def_panel_eff *= max(0.0, 1.0 - buff54_yang_def_from_attacker)

    if ctx.flags.get("pierce_def_buffs"):
        def_mult = 1.0
    else:
        def_mult = get_buff_multiplier(defender, 2 if def_type == "yang" else 4)

    base_def = def_panel_eff * def_mult
    if base_def <= 1e-9:
        base_def = 1.0

    return {
        "def_panel": def_panel,
        "def_flat_580": def_flat,
        "def_panel_eff": def_panel_eff,
        "buff54_yang_def_from_attacker": buff54_yang_def_from_attacker,
        "def_mult": def_mult,
        "base_def": base_def,
    }

def _killer_triggers(attack_entry: Dict[str, Any], defender: CharacterInstance) -> bool:
    killers = set(int(x) for x in (attack_entry.get("killers", []) or []))
    tribe = set(int(x) for x in (defender.character_info.get("tribe", []) or []))
    return len(killers & tribe) > 0


def _calc_hit_and_crit(mgr: CharacterInstanceManager, attacker: CharacterInstance, defender: CharacterInstance, attack_entry: Dict[str, Any], ctx: DamageContext) -> Dict[str, Any]:
    """命中率补正 / 暴击补正期望值
    不做随机判定，直接返回期望乘区。
    """
    hit_info = _get_hit_correction(attacker, defender, attack_entry, ctx)
    crit_info = _get_crit_expectation(mgr, attacker, defender, attack_entry)

    return {
        "acc": hit_info["acc"],
        "hit_diff": hit_info["hit_diff"],
        "hit_mult": hit_info["hit_mult"],
        "hit_correction": hit_info["hit_correction"],
        "guaranteed_hit": hit_info["guaranteed_hit"],

        "cri": crit_info["cri"],
        "killer": crit_info["killer"],
        "crit_mode": crit_info["crit_mode"],
        "crit_hit_diff": crit_info["crit_hit_diff"],
        "crit_hit_mult": crit_info["crit_hit_mult"],
        "crit_rate": crit_info["crit_rate"],
        "crit_atk_l1": crit_info["crit_atk_l1"],
        "crit_atk_l2": crit_info["crit_atk_l2"],
        "crit_atk_mult_1": crit_info["crit_atk_mult_1"],
        "crit_atk_mult_2": crit_info["crit_atk_mult_2"],
        "crit_bonus": crit_info["crit_bonus"],
        "crit_correction": crit_info["crit_correction"],
    }

def calc_damage_one_target(
    mgr: CharacterInstanceManager,
    ctx: DamageContext,
    shot_ctx: ShotContext,
) -> Dict[str, Any]:
    """对一个敌方目标计算本 seg 的单发伤害，并扣血。"""
    attacker = mgr.get_character_instance("我方前排", ctx.attacker_pos)
    defender = mgr.get_character_instance("敌方", ctx.enemy_pos)
    if attacker is None or defender is None:
        raise ValueError("attacker/defender 缺失")

    ae = shot_ctx.attack_entry

    # 选择防御类型（阳/阴）
    def_type = _choose_def_type(ae, ctx)

    # 我方/敌方基础攻防
    atk_info = _compute_base_atk(attacker, ctx, def_type)
    def_info = _compute_base_def(attacker, defender, ctx, def_type)

    # 威力（damage 字段）
    power = float(ae.get("damage", 0.0))

    # 角色等级补正（暂按 1.0/1.4）
    level_mult = _get_level_multiplier(attacker)

    # 弹幕等级补正（damage_extend[5]）
    danmaku_mult = float(shot_ctx.danmaku_extend_pct)

    # 绘卷补正（TODO）
    scroll_mult = 1.0

    # 基本伤害
    base_damage = (atk_info["base_atk"] / def_info["base_def"]) * power * scroll_mult * level_mult * danmaku_mult

    # 命中率补正 / 暴击补正期望值
    hc = _calc_hit_and_crit(mgr, attacker, defender, ae, ctx)

    hit_correction = float(hc["hit_correction"])
    crit_correction = float(hc["crit_correction"])

    element_info = _get_element_correction(attacker, defender, ae)
    element_correction = float(element_info["element_correction"])

    bullet_type_info = _get_bullet_type_correction(attacker, defender, ae)
    bullet_type_correction = float(bullet_type_info["bullet_type_correction"])

    buff47 = _get_buff47_frontline_effects(mgr, attacker)
    buff48 = _get_buff48_correction(attacker, ctx)

    buff54_damage_correction = _get_buff54_damage_correction(attacker)

    other_correction = (
        float(buff47["damage_correction"])
        * float(buff48["buff48_correction"])
        * float(buff54_damage_correction)
    )

    final_damage = (
        base_damage
        * hit_correction
        * crit_correction
        * element_correction
        * bullet_type_correction
        * other_correction
    )

    # 扣血（取整策略你后续再定；先用 int(round)）
    before_hp = defender.stats.hp
    dmg_i = int(round(final_damage))
    if dmg_i < 0:
        dmg_i = 0
    defender.damage(dmg_i)
    after_hp = defender.stats.hp

    return {
        "attacker_pos": ctx.attacker_pos,
        "enemy_pos": ctx.enemy_pos,
        "attack_type": shot_ctx.attack_type,
        "seg": shot_ctx.seg,
        "spirit_level": shot_ctx.spirit_level,
        "def_type": def_type,
        "power": power,
        "level_mult": level_mult,
        "danmaku_mult": danmaku_mult,
        "base_atk": atk_info["base_atk"],
        "base_def": def_info["base_def"],
        "base_damage": base_damage,
        "hit_correction": hit_correction,
        "crit_correction": crit_correction,
        "final_damage": final_damage,
        "damage_int": dmg_i,
        "before_hp": before_hp,
        "after_hp": after_hp,
        "hit": hc,
        "atk_info": atk_info,
        "def_info": def_info,
        "flags": dict(ctx.flags),
        "unhandled_effects": list(ctx.unhandled_effects),
        "shot_name": ae.get("name"),
        "attack_id": ae.get("attack_id"),
        "bullet_type": ae.get("type"),
        "element": ae.get("element"),
        "yinyang": ae.get("yinyang"),
        "killers": ae.get("killers", []),
        "element_correction": element_correction,
        "element_info": element_info,
        "bullet_type_correction": bullet_type_correction,
        "bullet_type_info": bullet_type_info,
        "other_correction": other_correction,
        "buff47_info": buff47,
        "buff48_info": buff48,
        "pre_barrier_stock": ctx.runtime_overrides.get("barrier_stock_before_attack"),
        "pre_spirit_stock": ctx.runtime_overrides.get("spirit_stock_before_attack"),
        "buff54_damage_correction": buff54_damage_correction,
    }


# ============================================================
# 执行：单攻击者攻击阶段
# ============================================================

def _iter_enemy_positions(mgr: CharacterInstanceManager) -> List[int]:
    """返回当前存在的敌方位置列表（0/1/2 里存在的）。"""
    res = []
    for p in (0, 1, 2):
        if mgr.get_character_instance("敌方", p) is not None:
            res.append(p)
    return res


def execute_attack_phase_for_attacker(
    mgr: CharacterInstanceManager,
    op: BattleOpStateManager,
    *,
    attacker_pos: int,
    segment_order: List[int],
    debug_print: bool = True,
) -> List[Dict[str, Any]]:
    """按 segment_order 执行单个攻击者的攻击阶段。

    - target=1：每个 seg 只对当前目标 enemy_pos 计算一次
    - target=2：每个 seg 对每个敌方都计算一次

    首发：段落内 buff 只执行一次；effects_1（12~16）对每个敌方执行一次。
    """

    attacker = mgr.get_character_instance("我方前排", attacker_pos)
    if attacker is None:
        raise ValueError(f"attacker 不存在 pos={attacker_pos}")

    details: List[Dict[str, Any]] = []

    try:
        for i, seg in enumerate(segment_order, start=1):
            first = first_launch_and_mark(attacker, seg)
            shot_ctx = build_shot_ctx(mgr, op, attacker_pos, seg=seg)

            paragraph_buffs, effects = extract_paragraph_payload(shot_ctx.attack_entry)
            effects_1, effects_2 = split_effects(effects)

            # 目标列表
            if shot_ctx.target_mode == 2:
                targets = _iter_enemy_positions(mgr)
            else:
                targets = [int(op.get_enemy_target_pos(attacker_pos))]

            log: Dict[str, Any] = {
                "i": i,
                "seg": seg,
                "first": first,
                "attack_type": shot_ctx.attack_type,
                "spirit_level": shot_ctx.spirit_level,
                "target_mode": shot_ctx.target_mode,
                "targets": targets,
                "pbuffs_count": len(paragraph_buffs),
                "effects_count": len(effects),
                "effects1_count": len(effects_1),
                "effects2_count": len(effects_2),
            }

            # 仅首发：段落内 buff（只执行一次）
            if first:
                if paragraph_buffs:
                    r = op.execute_paragraph_buffs(
                        char_manager=mgr,
                        front_pos=attacker_pos,
                        paragraph_buffs=paragraph_buffs,
                        is_first_launch=True,
                    )
                    log["paragraph_buff_result"] = r
                else:
                    log["pbuffs_skip"] = True

                # 仅首发：effects_1 对每个敌方执行一次
                if effects_1:
                    for ep in targets:
                        apply_effects_1_once_for_defender(mgr, ep, effects_1, log=log)
                else:
                    log["effects1_skip"] = True

            # 每发：对每个目标分别执行 effects2 + calc
            for enemy_pos in targets:
                ctx = DamageContext(
                    attacker_pos=attacker_pos,
                    enemy_pos=enemy_pos,
                    attack_type=shot_ctx.attack_type,
                    spirit_level=shot_ctx.spirit_level,
                    seg=seg,
                )

                op_status = op.get_op_status(attacker_pos)
                ctx.runtime_overrides["barrier_stock_before_attack"] = int(
                    getattr(op_status, "pre_shield_active_barrier_count", 0)
                )
                ctx.runtime_overrides["spirit_stock_before_attack"] = float(
                    getattr(op_status, "pre_spirit_value", 0.0)
                )
                ctx.runtime_overrides["actual_spirit_level"] = int(
                    getattr(op_status, "spirit_level", 0)
                )

                if effects_2:
                    apply_effects_2_per_hit(mgr, attacker_pos, effects_2, ctx, log=log)
                else:
                    log.setdefault("effects2_skip", True)

                d = calc_damage_one_target(mgr, ctx, shot_ctx)
                d["debug"] = dict(log)
                details.append(d)

                if debug_print:
                    extra = ""
                    if log.get("pbuffs_skip"):
                        extra += " (skip buffs)"
                    if log.get("effects1_skip"):
                        extra += " (skip e1)"
                    print(
                        f"[HIT {i:02d}] seg={seg} first={first} tgt={shot_ctx.target_mode} enemy_pos={enemy_pos} "
                        f"pbuffs={len(paragraph_buffs)} e1={len(effects_1)} e2={len(effects_2)} "
                        f"dmg={d['damage_int']} hp:{d['before_hp']}->{d['after_hp']}" + extra
                    )

        return details

    finally:
        reset_paragraph_executed(attacker)
        if debug_print:
            print("[RESET] attacker.paragraph_executed ->", attacker.paragraph_executed)


# ============================================================
# Smoke 断言（需要注意：target=2 时，details 数会是 len(segment_order)*len(targets)）
# ============================================================

def assert_A1_gate_once(details):
    """
    适配 target=2 多目标情况：
    - 同一轮（同一个 i、同一个 seg）的多条 detail 允许 first 都为 True
    - 只有当 seg 在后续轮次再次出现时，first 才必须为 False
    """
    # 先按“轮次 i”聚合
    by_i = {}
    for d in details:
        debug = d.get("debug", {}) or {}
        i = int(debug.get("i"))
        seg = int(d.get("seg"))
        first = bool(debug.get("first"))

        if i not in by_i:
            by_i[i] = {"seg": seg, "first": first}
        else:
            # 同一轮里的多目标 detail，seg/first 必须一致
            if by_i[i]["seg"] != seg:
                raise AssertionError(
                    f"A1 失败：同一轮 i={i} 出现不同 seg，"
                    f"{by_i[i]['seg']} vs {seg}"
                )
            if by_i[i]["first"] != first:
                raise AssertionError(
                    f"A1 失败：同一轮 i={i} 的 first 不一致，"
                    f"{by_i[i]['first']} vs {first}"
                )

    # 再按轮次顺序检查 gate
    seen_seg = set()
    for i in sorted(by_i.keys()):
        seg = by_i[i]["seg"]
        first = by_i[i]["first"]

        if seg not in seen_seg:
            if first is not True:
                raise AssertionError(f"A1 失败：seg={seg} 首次出现应 first=True（i={i}）")
            seen_seg.add(seg)
        else:
            if first is True:
                raise AssertionError(f"A1 失败：seg={seg} 再次出现不应 first=True（i={i}）")


def assert_C3_hp_sum(mgr: CharacterInstanceManager, enemy_pos: int, before_hp: int, details: List[Dict[str, Any]]):
    defender = mgr.get_character_instance("敌方", enemy_pos)
    if defender is None:
        return
    total = sum(int(d.get("damage_int", 0)) for d in details if int(d.get("enemy_pos")) == enemy_pos)
    expected = max(0, int(before_hp) - total)
    if defender.stats.hp != expected:
        raise AssertionError(f"C3 失败：enemy_pos={enemy_pos} hp={defender.stats.hp} expected={expected} (before={before_hp}, total={total})")
