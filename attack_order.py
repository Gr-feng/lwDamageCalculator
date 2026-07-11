# attack_order.py (v3)
# 目标：只依赖 CharacterInstanceManager / CharacterInstance 的最终状态字段
# 计算我方前排(0/1/2)的出手顺序，并提供可验证的 debug 输出。

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Union

from character import CharacterInstanceManager, CharacterInstance


# =========================
# Data model
# =========================

@dataclass(frozen=True)
class AttackOrderEntry:
    """用于验证/打印的“单角色关键状态快照”。"""

    pos: int
    exists: bool
    eligible: bool
    reason: str

    hp: int
    is_stunned: bool

    base_spd: int

    barrier_status_2: int
    freeze_barriers: int

    effective_spd: int


# =========================
# Helpers
# =========================

def _safe_int(v, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _buff_value_to_multiplier(value: float) -> float:
    """数值类 buff 层数倍率：
    value>=0: 1 + 0.3*value
    value<0 : 1 / (1 + 0.3*abs(value))
    """
    try:
        v = float(value)
    except Exception:
        v = 0.0

    if v >= 0:
        return 1.0 + 0.3 * v
    return 1.0 / (1.0 + 0.3 * abs(v))


def calc_effective_spd(char: CharacterInstance) -> int:
    """计算“有效速度 (effective spd)”，用于 attack order 排序。

    口径（按你最新规则）：

    1) base_spd = char.stats.spd

    2) 读取角色的 buffs 列表并影响速度：
       - buff_id==8：
         - sub_id==1 -> spd *= 10
         - sub_id==2 -> spd /= 10
       - buff_id==1 且 sub_id==5：spd *= f(value)
       - buff_id==41 且 sub_id==5：spd *= f(value)
         其中 f(value) = (1+0.3*value) if value>=0 else 1/(1+0.3*abs(value))

    3) 结界衰减（冻结异常）：
       - 角色 barriers 中，每有一个 barrier.type==2 -> spd *= 0.875（叠加乘算）
       - 若 char.stats.barrier_status_2 == 2，则忽略该衰减（免疫该类型异常）

    返回 int(round(spd))，保证排序稳定可复现。
    """

    spd = float(_safe_int(getattr(char.stats, "spd", 0), 0))

    # --- buff 影响 ---
    buffs = getattr(char, "buffs", None) or []

    # 先处理 8 系列（乘10/除10）
    for b in buffs:
        bid = getattr(b, "buff_id", None)
        sid = getattr(b, "sub_id", None)
        if bid == 8:
            if sid == 1:
                spd *= 10.0
            elif sid == 2:
                spd /= 10.0

    # 再处理 1/41 的 sub_id==5 数值倍率
    for b in buffs:
        bid = getattr(b, "buff_id", None)
        sid = getattr(b, "sub_id", None)
        if sid != 5:
            continue
        if bid == 1 or bid == 41:
            spd *= _buff_value_to_multiplier(getattr(b, "value", 0.0))

    # --- 冻结结界衰减 ---
    barrier_status_2 = _safe_int(getattr(char.stats, "barrier_status_2", 0), 0)
    if barrier_status_2 != 2:
        bars = getattr(char, "barriers", None) or []
        freeze_cnt = sum(1 for bb in bars if getattr(bb, "type", 0) == 2)
        if freeze_cnt > 0:
            spd *= (0.875 ** freeze_cnt)

    return int(round(spd))


def build_front_attack_order_snapshot(
    char_manager: CharacterInstanceManager,
    *,
    positions: Tuple[int, int, int] = (0, 1, 2),
) -> List[AttackOrderEntry]:
    """收集我方前排 0/1/2 的关键状态，用于排序+验证输出。"""

    out: List[AttackOrderEntry] = []

    for pos in positions:
        inst = char_manager.get_character_instance("我方前排", pos)
        if inst is None:
            out.append(
                AttackOrderEntry(
                    pos=pos,
                    exists=False,
                    eligible=False,
                    reason="角色不存在",
                    hp=0,
                    is_stunned=False,
                    base_spd=0,
                    barrier_status_2=0,
                    freeze_barriers=0,
                    effective_spd=0,
                )
            )
            continue

        hp = _safe_int(getattr(inst.stats, "hp", 0), 0)
        stunned = bool(getattr(inst, "is_stunned", False))

        # 行动过滤（从简单开始）
        if hp <= 0:
            eligible = False
            reason = "hp<=0"
        elif stunned:
            eligible = False
            reason = "is_stunned==True"
        else:
            eligible = True
            reason = "OK"

        base_spd = _safe_int(getattr(inst.stats, "spd", 0), 0)
        barrier_status_2 = _safe_int(getattr(inst.stats, "barrier_status_2", 0), 0)
        bars = getattr(inst, "barriers", None) or []
        freeze_cnt = sum(1 for bb in bars if getattr(bb, "type", 0) == 2)

        eff_spd = calc_effective_spd(inst)

        out.append(
            AttackOrderEntry(
                pos=pos,
                exists=True,
                eligible=eligible,
                reason=reason,
                hp=hp,
                is_stunned=stunned,
                base_spd=base_spd,
                barrier_status_2=barrier_status_2,
                freeze_barriers=freeze_cnt,
                effective_spd=eff_spd,
            )
        )

    return out


# =========================
# Public API (recommended)
# =========================

def get_ally_front_attack_order(
    char_manager: CharacterInstanceManager,
    *,
    return_debug: bool = False,
) -> Union[List[int], Tuple[List[int], List[AttackOrderEntry]]]:
    """计算我方前排出手顺序。

    最小可用：返回 positions 列表，例如 [1,0] / [2,0,1]（只包含“可行动”的角色）

    可扩展（return_debug=True）：返回 (order, snapshot)
      - order：最终出手顺序
      - snapshot：长度为3的 AttackOrderEntry 列表，包含每个位置的关键状态快照

    排序规则：
      - 仅对我方前排 0/1/2
      - 过滤：None / hp<=0 / is_stunned
      - 依据：effective_spd 降序
      - tie-break：pos 升序（0<1<2），稳定可复现
    """

    snapshot = build_front_attack_order_snapshot(char_manager)

    eligibles = [e for e in snapshot if e.eligible]

    # speed desc + position asc
    eligibles_sorted = sorted(eligibles, key=lambda e: (-e.effective_spd, e.pos))
    order = [e.pos for e in eligibles_sorted]

    if return_debug:
        return order, snapshot
    return order


# =========================
# Segment order parser (keep)
# =========================

def parse_attack_segment_order(
    attack_skill_data: Dict,
    spirit_level: int,
) -> List[int]:
    """解析攻击段落顺序（spirit 影响 all_order）。

    返回值统一为 **0-based 段落下标列表**。

    当前只支持两种合法口径：

    1) 模式1：`global_attributes['all_order_{spirit_level}']` 非 0
       - 例如 `"123g"` / `"112233g"`
       - 原始字符通常是 1-based，所以返回时统一 `-1`

    2) 模式2-顺序填满（你说的 attack_type=5 这类）
       条件：
       - `all_order_0 == 0`
       - 且没有有效的 `all_order_1 ~ all_order_3`

       处理方式：
       - **不读取** `attacks[*]['order']`（因为你已确认这个口径不该用）
       - 直接按 `attacks` 的 0-based 下标顺序填满
       - 对每个 `boost <= spirit_level` 的段落 idx，输出 `[idx] * amt`

       例：spirit=2，6段 boost=0,1,1,1,2,3，amt=10,4,4,4,4,4
       -> `[0]*10 + [1]*4 + [2]*4 + [3]*4 + [4]*4`

    若两种模式都不匹配，则直接报错，避免静默走错逻辑。
    """

    global_attrs = attack_skill_data.get("global_attributes", {}) or {}
    attacks = attack_skill_data.get("attacks", []) or []

    # -------------------------
    # 模式1：优先读取 all_order_{spirit_level}
    # -------------------------
    order_key = f"all_order_{spirit_level}"
    order_value = global_attrs.get(order_key, 0)
    order_str = str(order_value) if order_value is not None else ""

    # 非 0 视为有效模式1
    if order_str and order_str != "0":
        clean_str = order_str.rstrip("g")
        return [int(ch) - 1 for ch in clean_str if ch.isdigit()]

    # -------------------------
    # 模式2：顺序填满（按 attacks 下标）
    # 条件：all_order_0 == 0 且 all_order_1~3 都不存在/为0
    # -------------------------
    all_order_0 = global_attrs.get("all_order_0", 0)
    has_valid_all_order_1_3 = any(
        str(global_attrs.get(k, 0)) != "0"
        for k in ("all_order_1", "all_order_2", "all_order_3")
    )

    if str(all_order_0) == "0" and not has_valid_all_order_1_3:
        segment_order: List[int] = []
        for idx, attack in enumerate(attacks):
            boost = int(attack.get("boost", 0) or 0)
            if boost <= spirit_level:
                amt = int(attack.get("amt", 1) or 1)
                segment_order.extend([idx] * amt)
        return segment_order

    raise ValueError(
        "无法解析攻击段落顺序：既不是有效的 all_order 模式，也不是顺序填满模式。"
        f" spirit_level={spirit_level}, available_keys={list(global_attrs.keys())}"
    )

