from dataclasses import dataclass, field
from typing import Dict, List, Union, Literal, Optional, Any
import traceback
# 类型别名
AttackType = Literal["1", "2", "1c", "2c", "5"]
SpiritLevel = Literal[0, 1, 2, 3]
TargetType = Literal[1, 2, 3, 4]  # 1=自身，2=己方全体，3=敌方单体，4=敌方全体
EnemyPos = Literal[0, 1, 2]  # 敌方位置索引：0=敌方1号位，1=敌方2号位，2=敌方3号位

@dataclass
class AllyFrontOpStatus:
    """我方前排单角色操作状态（仅存储核心战斗配置）"""
    shield_open_count: int = 0
    attack_type: AttackType = "5"
    spirit_level: SpiritLevel = 0
    enemy_pos: EnemyPos = 0

    # ✅ 新增：快照（用于后续伤害计算读取）
    pre_shield_active_barrier_count: int = 0   # 执行“盾阶段”前：active 护盾数量
    pre_spirit_value: float = 0.0              # 执行“灵力阶段”前：spirit 数值（可保留小数）

class BattleOpStateManager:
    """战斗操作状态管理器（最终版）"""
    def __init__(self):
        # 我方前排3角色操作状态（1/2/3位置）
        self.ally_front_op_states: Dict[int, AllyFrontOpStatus] = {
            0: AllyFrontOpStatus(),
            1: AllyFrontOpStatus(),
            2: AllyFrontOpStatus()
        }
        # 全局技能执行顺序 - 二维列表 [[角色位置0~2, 技能位置0~2], ...]
        self.skill_order: List[List[int]] = []
        # key: (team_type, pos, subid)  value: {"kind": int, "count": int}
        self.pending_barrier_status_triggers = {}
        self._in_shield_phase = False
        self.field_buffs: Dict[str, Dict[int, float]] = {
            "bullet_type": {},
            "element": {},
            "type_resist": {},
            "killer_crit_bonus": {},
        }

    # -------------------------- 敌方目标位置管理（新增） --------------------------
    def set_enemy_target_pos(self, front_pos: int, enemy_pos: EnemyPos):
        """
        设置我方前排角色指向的敌方单体目标位置
        :param front_pos: 我方前排角色位置（1/2/3）
        :param enemy_pos: 敌方位置索引（0=敌方1号位，1=敌方2号位，2=敌方3号位）
        """
        if front_pos not in [0,1,2]:
            raise ValueError("我方前排位置只能是0/1/2")
        if enemy_pos not in [0,1,2]:
            raise ValueError("敌方目标位置只能是0/1/2（对应敌方1/2/3号位）")
        
        self.ally_front_op_states[front_pos].enemy_pos = enemy_pos

    def get_enemy_target_pos(self, front_pos: int) -> EnemyPos:
        """
        获取我方前排角色指向的敌方单体目标位置
        :param front_pos: 我方前排角色位置（1/2/3）
        :return: 敌方位置索引（0/1/2）
        """
        if front_pos not in [0,1,2]:
            raise ValueError("我方前排位置只能是0/1/2")
        return self.ally_front_op_states[front_pos].enemy_pos

    @staticmethod
    def resolve_enemy_target_pos(char_manager: Any, preferred_enemy_pos: int) -> EnemyPos:
        preferred = int(preferred_enemy_pos)
        if preferred in (0, 1, 2) and char_manager.get_character_instance("敌方", preferred) is not None:
            return preferred
        for enemy_pos in (0, 1, 2):
            if char_manager.get_character_instance("敌方", enemy_pos) is not None:
                return enemy_pos
        return 0

    def reset_enemy_target_pos(self, front_pos: int = None):
        """
        重置敌方目标位置为默认值0
        :param front_pos: 可选，指定角色位置（1/2/3）；None则重置所有角色
        """
        if front_pos is None:
            # 重置所有角色
            for pos in [0,1,2]:
                self.ally_front_op_states[pos].enemy_pos = 0
        else:
            if front_pos not in [0,1,2]:
                raise ValueError("我方前排位置只能是0/1/2")
            self.ally_front_op_states[front_pos].enemy_pos = 0

    # -------------------------- 技能顺序管理 --------------------------
    def set_skill_order(self, skill_order: List[List[int]]):
        """设置全局技能执行顺序"""
        for item in skill_order:
            if len(item) != 2:
                raise ValueError("技能执行顺序项必须是长度为2的列表 [角色位置0~2, 技能位置0~2]")
            char_pos_idx, skill_pos_idx = item
            if not (0 <= char_pos_idx <= 2):
                raise ValueError("角色位置必须是0~2（对应我方前排1~3号位）")
            if skill_pos_idx < 0:
                raise ValueError("技能位置不能为负数")
        self.skill_order = skill_order

    def add_skill_order_item(self, char_pos_idx: int, skill_pos_idx: int):
        """添加单个技能执行顺序项"""
        if not (0 <= char_pos_idx <= 2):
            raise ValueError("角色位置必须是0~2（对应我方前排1~3号位）")
        if skill_pos_idx < 0:
            raise ValueError("技能位置不能为负数")
        self.skill_order.append([char_pos_idx, skill_pos_idx])

    def clear_skill_order(self):
        """清空技能执行顺序"""
        self.skill_order = []

    def set_field_buffs(self, field_buffs: Optional[Dict[str, Dict[int, float]]]):
        field_buffs = field_buffs or {}
        normalized: Dict[str, Dict[int, float]] = {
            "bullet_type": {},
            "element": {},
            "type_resist": {},
            "killer_crit_bonus": {},
        }
        for group_name in normalized:
            raw_group = field_buffs.get(group_name, {}) or {}
            for key, value in raw_group.items():
                normalized[group_name][int(key)] = float(value)
        self.field_buffs = normalized

    def get_field_buffs(self) -> Dict[str, Dict[int, float]]:
        return {
            group_name: dict(group_values)
            for group_name, group_values in self.field_buffs.items()
        }

    # -------------------------- 角色操作状态设置 --------------------------
    def set_shield_open_count(self, front_pos: int, count: int):
        """设置我方前排角色开启的护盾数量（0~3）"""
        if front_pos not in [0,1,2]:
            raise ValueError("我方前排位置只能是0/1/2")
        if not (0 <= count <= 3):
            raise ValueError("开启的护盾数量必须是0~3")
        self.ally_front_op_states[front_pos].shield_open_count = count

    def set_attack_params(self, front_pos: int, attack_type: AttackType = "5", spirit_level: SpiritLevel = 0):
        """设置我方前排角色的攻击参数（攻击类型、灵力等级）"""
        if front_pos not in [0,1,2]:
            raise ValueError("我方前排位置只能是0/1/2")
        if not (0 <= spirit_level <= 3):
            raise ValueError("灵力等级必须是0~3")
        
        op_state = self.ally_front_op_states[front_pos]
        op_state.attack_type = attack_type
        op_state.spirit_level = spirit_level

    # -------------------------- 角色操作状态获取 --------------------------
    def get_op_status(self, front_pos: int) -> AllyFrontOpStatus:
        """获取我方前排角色的操作状态"""
        if front_pos not in [0,1,2]:
            raise ValueError("我方前排位置只能是0/1/2")
        return self.ally_front_op_states[front_pos]

    def get_skill_order(self) -> List[List[int]]:
        """获取全局技能执行顺序"""
        return self.skill_order.copy()

    def get_shield_open_count(self, front_pos: int) -> int:
        """获取角色开启的护盾数量"""
        return self.get_op_status(front_pos).shield_open_count

    def get_attack_type(self, front_pos: int) -> AttackType:
        """获取角色攻击类型"""
        return self.get_op_status(front_pos).attack_type

    def get_spirit_level(self, front_pos: int) -> SpiritLevel:
        """获取角色灵力等级"""
        return self.get_op_status(front_pos).spirit_level

    # -------------------------- 状态重置 --------------------------
    def reset(self):
        """重置所有操作状态"""
        self.ally_front_op_states = {
            0: AllyFrontOpStatus(),
            1: AllyFrontOpStatus(),
            2: AllyFrontOpStatus()
        }
        self.skill_order = []
        # key: (team_type, pos, subid)  value: {"kind": int, "count": int}
        self.pending_barrier_status_triggers = {}
        self._in_shield_phase = False
        self.field_buffs = {
            "bullet_type": {},
            "element": {},
            "type_resist": {},
            "killer_crit_bonus": {},
        }

    # -------------------------- 通用Buff处理函数（核心） --------------------------
    def _apply_buff_effect(
        self,
        effect_list: List[int],
        char_manager: Any,
        attacker_pos_idx: int,
        enemy_target_pos_idx: int = 0,
    ) -> int:
        """
        通用Buff效果处理函数（只负责把Buff写入到CharacterInstanceManager中）
        :param effect_list: 5参数buff列表 [buff_id, sub_id, target_type, duration, value]
        :param char_manager: CharacterInstanceManager实例
        :param attacker_pos_idx: 我方前排位置索引（0~2）
        :param enemy_target_pos_idx: 敌方目标位置索引（0~2，默认0）
        :return: 实际写入的Buff条数
        """
        if len(effect_list) == 0:
            return 0
        elif len(effect_list) != 5:
            raise ValueError(f"Buff效果列表必须包含5个参数，当前：{effect_list}")

        buff_id, sub_id, target_type, duration, value = effect_list

        # ----------------------------
        # ID=1: sub_id>=100 的打包拆分
        # 例如 408 -> 4 和 08(=8)
        # ----------------------------
        if int(buff_id) == 1 and int(sub_id) >= 100:
            sid = int(sub_id)
            first = sid // 100          # 百位
            second = sid % 100          # 后两位（08 -> 8）

            applied = 0
            # 百位可能出现 0（例如 008 这种），按需跳过
            if first != 0:
                applied += int(self._apply_buff_effect(
                    effect_list=[1, int(first), int(target_type), int(duration), value],
                    char_manager=char_manager,
                    attacker_pos_idx=attacker_pos_idx,
                    enemy_target_pos_idx=enemy_target_pos_idx,
                ))
            if second != 0:
                applied += int(self._apply_buff_effect(
                    effect_list=[1, int(second), int(target_type), int(duration), value],
                    char_manager=char_manager,
                    attacker_pos_idx=attacker_pos_idx,
                    enemy_target_pos_idx=enemy_target_pos_idx,
                ))
            return applied
        
        target_type = int(target_type)

        # ✅ 兼容：某些数据里 0 表示“默认我方全体”
        if target_type == 0:
            target_type = 2

        if target_type not in (1, 2, 3, 4):
            raise ValueError(f"不支持的目标类型：{target_type}（仅支持0~4，其中0视为2）")

        # 计算目标（team_type, pos）
        targets: List[tuple[str, int]] = []
        if target_type == 1:
            targets = [("我方前排", int(attacker_pos_idx))]
        elif target_type == 2:
            targets = [("我方前排", p) for p in (0, 1, 2)]
        elif target_type == 3:
            resolved_enemy_pos = self.resolve_enemy_target_pos(char_manager, int(enemy_target_pos_idx))
            targets = [("敌方", int(resolved_enemy_pos))]
        elif target_type == 4:
            targets = [("敌方", p) for p in (0, 1, 2)]

        # ===== 特殊Buff：在 OpState 阶段直接产生“状态变更”，而不是写入 buffs 列表 =====
        # 4 结界增加：value=增加结界数量（调用 CharacterInstance.add_barrier）
        # 5 灵力上升：value=增加灵力（调用 CharacterInstance.update_spirit(mode='add')）
        # 6 附加结界异常：sub_id=异常类型(1燃烧/2冻结/3感电/4毒雾/5黑暗)，value=修改的结界数量
        #    调用 CharacterInstance.set_barrier_type(n=value, barrier_type=sub_id)
        special_id = int(buff_id)

        applied = 0
        for team_type, pos in targets:
            inst = char_manager.get_character_instance(team_type, pos)
            if inst is None:
                continue

            if special_id == 4:
                inst.add_barrier(int(value))
                applied += 1
                continue

            if special_id == 5:
                # 注意：灵力上升的 value 口径为 20 = 1.0 灵力
                inst.update_spirit(float(value) / 20.0, mode="add")
                applied += 1
                continue

            if special_id == 6:
                # 附加结界异常：sub_id=异常类型(1燃烧/2冻结/3感电/4毒雾/5黑暗)，value=尝试附加的数量
                # 需要记录实际改变数量，并根据 barrier_status_{sub_id} 触发后续效果
                bs_key = f"barrier_status_{int(sub_id)}"
                bs_kind = 0
                # barrier_status_* 通常在 stats 上；若缺失则视为 0
                try:
                    bs_kind = int(getattr(inst.stats, bs_key, 0))
                except Exception:
                    bs_kind = 0

                # kind=1：免疫这次异常（跳过 set_barrier_type）
                if bs_kind == 1:
                    applied += 1
                    continue

                changed = inst.set_barrier_type(int(value), int(sub_id))
                applied += int(changed)

                # 若实际未改变（无可用槽位等），则不触发后续
                if changed <= 0:
                    continue

                def _apply_to_same_inst(eff):
                    """把 eff 视为对当前 inst（team_type,pos）生效（忽略 eff[2] 的 target_type 字段）。"""
                    _bid, _sid, _t, _dur, _val = eff
                    _bid = int(_bid); _sid = int(_sid); _dur = int(_dur)
                    # 复用 _apply_buff_effect 的“负值映射”规则：2->1(-), 42->41(-)
                    if _bid == 2:
                        _bid = 1
                        _val = -float(_val)
                    elif _bid == 42:
                        _bid = 41
                        _val = -float(_val)

                    # 4/5/6/9 在 OpState 阶段直接改状态
                    if _bid == 4:
                        inst.add_barrier(int(_val))
                        return
                    if _bid == 5:
                        inst.update_spirit(float(_val) * 0.2, mode="add")
                        return
                    if _bid == 6:
                        inst.set_barrier_type(int(_val), int(_sid))
                        return
                    if _bid == 9:
                        # 去除异常：设置 n 个异常为 0
                        inst.set_barrier_type(int(_val), 0)
                        return

                    # 其他：写入 buffs 列表（走合并/限幅规则）
                    char_manager.add_character_buff(
                        team_type=team_type,
                        position=pos,
                        buff_id=_bid,
                        sub_id=_sid,
                        duration=_dur,
                        value=float(_val),
                    )

                # kind=6/7/8：常规“追加buff”类
                if bs_kind in (6, 7, 8):
                    # 如果处在“开盾阶段之前”（技能阶段），不要立刻触发：
                    # 因为开盾会把异常盾击破（inactive/type=0），触发次数要以开盾后剩余异常盾为准
                    if getattr(self, "_in_shield_phase", False):
                        # 什么都不做，等 _execute_shields 结束后 flush 扫描触发
                        continue
                    # ✅ 非 shield 阶段：只对敌方触发（我方不触发）
                    if team_type != "敌方":
                        continue
                    # 非开盾阶段（pre-attack / paragraph / 攻击单发 / post-attack）：
                    # 立即按“当前护盾状态”触发敌/我方的 barrier_status
                    self._trigger_barrier_status_for_inst(
                        char_manager=char_manager,
                        team_type=team_type,
                        pos=pos,
                        subid=int(sub_id),
                        times=int(changed),   # ✅ 关键：只按本次新增的数量触发
                    )
                    continue

                # 其它 kind：照旧立即处理
                if bs_kind == 5:
                    _apply_to_same_inst([5, 0, 1, 1, 4])
                elif bs_kind == 3:
                    self._apply_buff_effect(
                        effect_list=[6, int(sub_id), 3, 1, int(changed)],
                        char_manager=char_manager,
                        attacker_pos_idx=attacker_pos_idx,
                        enemy_target_pos_idx=enemy_target_pos_idx,
                    )
                # 0/2/4 或其它：无额外处理
                continue

            # =============================
            # 58 蓄积：A→B（把面板A按比例换算成固定加值，写入 buff_id=580）
            # effect_list: [58, sub_id(1~25), target_type, duration, value_percent]
            # 例如 [58,2,2,3,20]：阳防→阳攻，给己方全体写入 buff 580（加到阳攻）
            # =============================
            if special_id == 58:
                sid = int(sub_id)
                if sid < 1 or sid > 25:
                    raise ValueError(f"蓄积 sub_id 超出范围(1~25)：{sid}")

                # A->B 解码（仅五项面板：阳攻/阳防/阴攻/阴防/速度）
                src = (sid - 1) % 5 + 1   # 1..5
                dst = (sid - 1) // 5 + 1  # 1..5

                # 映射到 CharacterStats 字段名（按你 character.py 常用命名写了多种兜底）
                def _get_panel_value(stats, stat_id: int) -> float:
                    # 1阳攻 2阳防 3阴攻 4阴防 5速度
                    candidates = {
                        1: ("yang_atk", "atk_yang", "yangAttack", "yang_attack"),
                        2: ("yang_def", "def_yang", "yangDefense", "yang_defense"),
                        3: ("yin_atk", "atk_yin", "yinAttack", "yin_attack"),
                        4: ("yin_def", "def_yin", "yinDefense", "yin_defense"),
                        5: ("spd", "speed", "agi"),
                    }[stat_id]
                    for key in candidates:
                        if hasattr(stats, key):
                            return float(getattr(stats, key) or 0.0)
                    return 0.0

                percent = float(value) / 100.0  # 20 -> 0.2
                a_val = _get_panel_value(inst.stats, src)
                add_val = a_val * percent

                # 写入 buff_id=580：sub_id 用“被提升的面板类型 dst(1..5)”
                char_manager.add_character_buff(
                    team_type=team_type,
                    position=pos,
                    buff_id=580,
                    sub_id=int(dst),
                    duration=int(duration),
                    value=float(add_val),
                )
                applied += 1
                continue

            # 54：互斥型，添加新 54 前先删除该角色身上所有旧 54
            if int(buff_id) == 54:
                inst.buffs = [b for b in inst.buffs if int(b.buff_id) != 54]

            if special_id == 2:
                mapped_id = 1
                mapped_value = -float(value)
                char_manager.add_character_buff(
                    team_type=team_type,
                    position=pos,
                    buff_id=mapped_id,
                    sub_id=int(sub_id),
                    duration=int(duration),
                    value=mapped_value,
                )
                applied += 1
                continue

            if special_id == 42:
                mapped_id = 41
                mapped_value = -float(value)
                char_manager.add_character_buff(
                    team_type=team_type,
                    position=pos,
                    buff_id=mapped_id,
                    sub_id=int(sub_id),
                    duration=int(duration),
                    value=mapped_value,
                )
                applied += 1
                continue


            # ===== 普通Buff：写入 buffs 列表（走合并/限幅规则） =====
            char_manager.add_character_buff(
                team_type=team_type,
                position=pos,
                buff_id=int(buff_id),
                sub_id=int(sub_id),
                duration=int(duration),
                value=float(value),
            )
            applied += 1

        return applied

    # -------------------------- 核心执行函数 --------------------------
    def execute_operation_state(self, char_manager: Any) -> Dict[str, Any]:
        """
        执行完整的战斗操作状态（攻击前流程）
        执行流程：技能 → 护盾 → 灵力 → 攻击前Buff
        :param char_manager: CharacterInstanceManager实例
        :return: 执行结果
        """
        # 1. 基础数据获取与校验
        ally_front_chars = [
            char_manager.get_character_instance("我方前排", 0),
            char_manager.get_character_instance("我方前排", 1),
            char_manager.get_character_instance("我方前排", 2)
        ]
        enemy_chars = [
            char_manager.get_character_instance("敌方", 0),
            char_manager.get_character_instance("敌方", 1),
            char_manager.get_character_instance("敌方", 2)
        ]
        
        if all(char is None for char in ally_front_chars):
            raise ValueError("我方前排无任何角色，无法执行战斗操作")
        
        # 初始化执行结果
        result = {
            "success": True,
            "errors": [],
            "skill_execution": [],
            "shield_execution": [],
            "spirit_execution": [],
            "pre_attack_buff_execution": []
        }

        try:
            # 2. 第一步：执行技能（含a/b/c buff处理）
            self._execute_skills(char_manager, ally_front_chars, enemy_chars, result)
            
            # 3. 第二步：执行护盾效果
            self._execute_shields(char_manager, ally_front_chars, result)
            
            # 4. 第三步：执行灵力效果
            self._execute_spirit(char_manager, ally_front_chars, result)
            
            # 5. 第四步：执行攻击前Buff
            self._execute_pre_attack_buffs(char_manager, ally_front_chars, enemy_chars, result)
            
        except Exception as e:
            result["success"] = False
            result["errors"].append(f"执行操作失败：{str(e)}")

        return result

    # -------------------------- 段落内Buff执行函数（新增） --------------------------
    def execute_paragraph_buffs(
        self,
        char_manager: Any,
        front_pos: int,
        paragraph_buffs: List[List[int]],
        is_first_launch: bool
    ) -> Dict[str, Any]:
        """
        段落内Buff执行函数（首发判定后调用）
        仅当 is_first_launch=True 时执行段落内buff，格式为二维5参数列表
        """
        result = {
            "success": True,
            "errors": [],
            "char_pos": front_pos,
            "is_first_launch": is_first_launch,
            "paragraph_buff_count": len(paragraph_buffs),
            "applied_buff_count": 0,
            "enemy_target_pos": self.get_enemy_target_pos(front_pos),
            "reason": ""
        }

        try:
            if not is_first_launch:
                result["reason"] = "非首发，跳过段落内Buff执行"
                return result

            if front_pos not in (0, 1, 2):
                raise ValueError(f"我方前排位置只能是0/1/2，当前：{front_pos}")

            char = char_manager.get_character_instance("我方前排", front_pos)
            if not char:
                raise ValueError(f"我方前排{front_pos}号位无角色，无法执行段落内Buff")

            if not isinstance(paragraph_buffs, list) or len(paragraph_buffs) == 0:
                result["reason"] = "段落内Buff列表为空，执行结束"
                return result

            def _normalize_effect(effect, idx):
                # 兼容 [[...]] 多包一层的情况
                if isinstance(effect, list) and len(effect) == 1 and isinstance(effect[0], list):
                    effect = effect[0]
                if not (isinstance(effect, list) and len(effect) == 5):
                    raise ValueError(f"第{idx}个段落Buff结构异常：{effect} (type={type(effect)})")
                return effect

            applied_count = 0
            enemy_target_pos = self.get_enemy_target_pos(front_pos)

            for idx, effect in enumerate(paragraph_buffs):
                try:
                    effect = _normalize_effect(effect, idx)
                    applied = self._apply_buff_effect(
                        effect_list=effect,
                        char_manager=char_manager,
                        attacker_pos_idx=front_pos,
                        enemy_target_pos_idx=enemy_target_pos,
                    )
                    applied_count += int(applied)
                except Exception as e:
                    err_msg = (
                        f"段落内Buff处理失败（attacker={front_pos}, enemy_target={enemy_target_pos}, "
                        f"idx={idx}, effect={effect}）：{str(e)}"
                    )
                    result["errors"].append(err_msg)

            result["applied_buff_count"] = applied_count
            result["reason"] = (
                f"首发判定为True，成功应用{applied_count}次（段落buff条数={len(paragraph_buffs)}，敌方目标={enemy_target_pos}）"
            )

            # 如果你希望“有错误就 success=False”，可以加：
            # if result["errors"]:
            #     result["success"] = False

            return result

        except Exception as e:
            result["success"] = False
            result["reason"] = f"段落内Buff执行异常：{str(e)}"
            result["errors"].append(result["reason"])
            return result
    # -------------------------- 内部执行方法 --------------------------

    def _trigger_barrier_status_for_inst( 
        self,
        char_manager: Any,
        team_type: str,
        pos: int,
        subid: int,
        times: Optional[int] = None,   # ✅ 新增
    ):
        inst = char_manager.get_character_instance(team_type, pos)
        if inst is None:
            return

        # kind 只看配置，不需要扫描护盾
        try:
            kind = int(getattr(inst.stats, f"barrier_status_{int(subid)}", 0))
        except Exception:
            kind = 0

        kind_to_subids = {
            6: (1, 3, 8, 10),
            7: (2, 4, 9, 11),
            8: (5, 6, 7),
        }
        if kind not in kind_to_subids:
            return

        # ✅ 默认行为：如果没给 times，就按当前 remain（兼容旧逻辑）
        if times is None:
            bars = getattr(inst, "barriers", None) or []
            times = sum(
                1 for b in bars
                if getattr(b, "is_active", False) and int(getattr(b, "type", 0)) == int(subid)
            )

        times = int(times)
        if times <= 0:
            return

        for _ in range(times):
            for sid in kind_to_subids[kind]:
                char_manager.add_character_buff(
                    team_type=team_type,
                    position=pos,
                    buff_id=1,
                    sub_id=int(sid),
                    duration=1,
                    value=1.0,
                )

    def _flush_pending_barrier_status_triggers(self, char_manager: Any, result: Dict[str, Any]):
        """
        在“开盾结束后”结算：根据角色当前护盾状态触发 barrier_status 效果
        规则（仅对 kind=6/7/8 生效）：
        - 遍历角色所有 active 护盾
        - 若护盾 type=t != 0，则读取 inst.stats.barrier_status_t 得到 kind
        - kind==6/7/8：对该角色自身各触发一次对应 buff 组
        - 每遇到一个符合条件的护盾就触发一次（所以触发次数=开盾后仍存在的异常盾数量）
        """
        kind_to_subids = {
            6: (1, 3, 8, 10),
            7: (2, 4, 9, 11),
            8: (5, 6, 7),
        }

        def apply_kind_buffs_to_inst(team_type: str, pos: int, kind: int):
            # 对该角色自身施加普通 buff（id=1，duration=1，value=1）
            for sid in kind_to_subids[kind]:
                char_manager.add_character_buff(
                    team_type=team_type,
                    position=pos,
                    buff_id=1,
                    sub_id=int(sid),
                    duration=1,
                    value=1.0,
                )

        # 需要扫描的队伍：我方前排 + 敌方（你现在异常也可能加到敌方）
        for team_type in ("我方前排", "敌方"):
            for pos in (0, 1, 2):
                inst = char_manager.get_character_instance(team_type, pos)
                if inst is None:
                    continue
                bars = getattr(inst, "barriers", None) or []
                if not bars:
                    continue

                for b in bars:
                    if not getattr(b, "is_active", False):
                        continue
                    t = int(getattr(b, "type", 0))
                    if t == 0:
                        continue

                    # 读取 barrier_status_t
                    kind = 0
                    try:
                        kind = int(getattr(inst.stats, f"barrier_status_{t}", 0))
                    except Exception:
                        kind = 0

                    # 只处理 kind=6/7/8（常规施加 buff）
                    if kind in (6, 7, 8):
                        apply_kind_buffs_to_inst(team_type, pos, kind)
                    # 其它 kind 在 id==6 处理阶段已经即时处理（或无效果），这里不再管

    def _execute_skills(self, char_manager: Any, ally_chars: List[Any], enemy_chars: List[Any], result: Dict[str, Any]):
        """执行技能效果：只负责把技能 a/b/c 三个词条原样交给 _apply_buff_effect 执行，不做额外处理。"""
        self._in_shield_phase = True
        for idx, order_item in enumerate(self.skill_order):
            char_pos_idx, skill_pos_idx = order_item
            display_pos = char_pos_idx + 1
            skill_exec_record = {
                "order_idx": idx,
                "char_pos_idx": char_pos_idx,
                "char_pos": display_pos,
                "skill_pos_idx": skill_pos_idx,
                "status": "success",
                "reason": "",
                "skill_id": None,
                "skill_name": "",
                "skill_effect": None,
                "applied_a_count": 0,
                "applied_b_count": 0,
                "applied_c_count": 0
            }

            try:
                caster = ally_chars[char_pos_idx]
                if not caster:
                    raise ValueError(f"我方前排{display_pos}号位无角色")

                if skill_pos_idx < 0 or skill_pos_idx >= len(caster.skills):
                    raise ValueError(f"角色{display_pos}号位无第{skill_pos_idx}个技能")

                target_skill = caster.skills[skill_pos_idx]
                skill_id = target_skill.skill_id

                skill_effect = char_manager.use_character_skill("我方前排", char_pos_idx, skill_id)
                if not skill_effect:
                    skill_exec_record["status"] = "failed"
                    skill_exec_record["skill_id"] = skill_id
                    skill_exec_record["skill_name"] = target_skill.name
                    skill_exec_record["reason"] = f"技能{skill_id}冷却中（剩余{target_skill.cur_cd}回合）"
                    result["skill_execution"].append(skill_exec_record)
                    continue

                skill_exec_record["skill_id"] = skill_id
                skill_exec_record["skill_name"] = target_skill.name
                skill_exec_record["skill_effect"] = skill_effect

                applied_a = applied_b = applied_c = 0

                # a：直接执行
                a = skill_effect.get("a")
                if isinstance(a, list) and len(a) == 5:
                    self._apply_buff_effect(
                        effect_list=a,
                        char_manager=char_manager,
                        attacker_pos_idx=char_pos_idx,
                        enemy_target_pos_idx=self.get_enemy_target_pos(char_pos_idx),
                    )
                    applied_a = 1

                # b：直接执行（若目标类型是敌方单体/全体，由 effect_list[2] 决定）
                b = skill_effect.get("b")
                if isinstance(b, list) and len(b) == 5:
                    self._apply_buff_effect(
                        effect_list=b,
                        char_manager=char_manager,
                        attacker_pos_idx=char_pos_idx,
                        enemy_target_pos_idx=self.get_enemy_target_pos(char_pos_idx),
                    )
                    applied_b = 1

                # c：直接执行
                c = skill_effect.get("c")
                if isinstance(c, list) and len(c) == 5:
                    self._apply_buff_effect(
                        effect_list=c,
                        char_manager=char_manager,
                        attacker_pos_idx=char_pos_idx,
                        enemy_target_pos_idx=self.get_enemy_target_pos(char_pos_idx),
                    )
                    applied_c = 1

                skill_exec_record["applied_a_count"] = applied_a
                skill_exec_record["applied_b_count"] = applied_b
                skill_exec_record["applied_c_count"] = applied_c
                skill_exec_record["reason"] = f"技能执行成功，已执行 a:{applied_a} b:{applied_b} c:{applied_c}"

            except Exception as e:
                skill_exec_record["status"] = "error"
                skill_exec_record["reason"] = str(e)
                result["errors"].append(f"技能执行失败（顺序{idx}）：{str(e)}")

            result["skill_execution"].append(skill_exec_record)

    def _execute_shields(self, char_manager: Any, ally_chars: List[Any], result: Dict[str, Any]):
        """执行护盾效果（击破护盾 + 触发 graze 相关 buff）

        规则：
        - 击破护盾时：如果击破后只剩 1 个 active 护盾，则停止继续击破（永远保留 1 个 active）。
        - 后续 buff 触发次数按“实际击破数量 broken_count”计算（不是配置的开盾数）。
        - graze_target 口径调整：2=自身、1=己方全体（需要映射到 _apply_buff_effect 的 1/2 口径：1=自身、2=己方全体）
        - graze_buff(=graze_type) 已知映射：
            * 6 -> [1,6,target,1,1]
            * 5 -> [1,5,target,1,1]
            * 3 -> [1,3,target,1,1]
        """
        self._in_shield_phase = True
        for front_pos in [0, 1, 2]:
            shield_exec_record = {
                "char_pos": front_pos,
                "status": "success",
                "reason": "",
                "shield_open_count": 0,
                "broken_count": 0,
                "buff_trigger_times": 0,
                "graze_target_raw": 0,
                "target_type": 0,
                "graze_type": 0,
            }

            try:
                char = char_manager.get_character_instance("我方前排", front_pos)
                if not char:
                    shield_exec_record["status"] = "skipped"
                    shield_exec_record["reason"] = "角色不存在"
                    result["shield_execution"].append(shield_exec_record)
                    continue

                # 1) 获取配置：开盾数
                op_status = self.get_op_status(front_pos)
                shield_open_count = int(op_status.shield_open_count)
                shield_exec_record["shield_open_count"] = shield_open_count

                # char 已存在后，写入盾前快照（active 护盾数量）
                pre_active = sum(1 for b in (char.barriers or []) if getattr(b, "is_active", False))
                self.get_op_status(front_pos).pre_shield_active_barrier_count = int(pre_active)

                if shield_open_count <= 0:
                    shield_exec_record["reason"] = "开盾数量为0，无需处理"
                    result["shield_execution"].append(shield_exec_record)
                    continue

                # 2) 按规则击破护盾：最多击破 shield_open_count 个，但永远保留 1 个 active
                broken_count = 0
                for _ in range(shield_open_count):
                    active_cnt = sum(1 for b in (char.barriers or []) if getattr(b, "is_active", False))
                    if active_cnt <= 1:
                        break  # 已经只剩 1 个 active，停止继续击破
                    one = char_manager.break_character_barrier("我方前排", front_pos, 0) or 0
                    if one <= 0:
                        break
                    broken_count += one

                shield_exec_record["broken_count"] = broken_count
                shield_exec_record["buff_trigger_times"] = broken_count


                if broken_count <= 0:
                    shield_exec_record["reason"] = "未击破护盾（可能已只剩1个active或无护盾）"
                    result["shield_execution"].append(shield_exec_record)
                    continue

                # 3) graze_target 口径调整：2=自身、1=己方全体、0=无（跳过后续buff阶段）
                graze_target_raw = int(getattr(char.stats, "graze_target", 0))
                shield_exec_record["graze_target_raw"] = graze_target_raw
                #if graze_target_raw == 0:
                    #shield_exec_record["reason"] = f"成功击破{broken_count}个护盾，但 graze_target=0（无开盾buff）"
                    #result["shield_execution"].append(shield_exec_record)
                    #continue
                if graze_target_raw not in (0, 1, 2):
                    raise ValueError(f"无效的护盾目标类型：{graze_target_raw}（仅支持0/1/2，其中2=自身，1=己方全体，0=无）")

                # 映射到 _apply_buff_effect：1=自身、2=己方全体
                mapped_target_type = 2 if graze_target_raw == 0 else 1
                shield_exec_record["target_type"] = mapped_target_type

                # 4) graze_type：用 stats.graze_buff 表示；0=无（跳过后续buff阶段）
                graze_type = int(getattr(char.stats, "graze_buff", 0))
                shield_exec_record["graze_type"] = graze_type
                if graze_type == 0:
                    shield_exec_record["reason"] = f"成功击破{broken_count}个护盾，但 graze_type=0（无开盾buff）"
                    result["shield_execution"].append(shield_exec_record)
                    continue

                # 5) 触发次数按 broken_count：映射 n -> [1,n,target,1,1]
                for _ in range(broken_count):
                    buff_effect = [1, graze_type, mapped_target_type, 1, 1]
                    self._apply_buff_effect(
                        effect_list=buff_effect,
                        char_manager=char_manager,
                        attacker_pos_idx=front_pos,
                        enemy_target_pos_idx=self.get_enemy_target_pos(front_pos),
                    )

                shield_exec_record["reason"] = (
                    f"成功击破{broken_count}个护盾（最多{shield_open_count}，且保留1个active），"
                    f"触发{broken_count}次buff（graze_type={graze_type}, target={mapped_target_type}）"
                )


            except Exception as e:
                shield_exec_record["status"] = "error"
                shield_exec_record["reason"] = str(e)
                result["errors"].append(f"护盾处理失败（角色{front_pos}）：{str(e)}")

            # 开盾阶段全部处理完成后，结算“延迟的 barrier_status(6/7/8) 触发”   
            result["shield_execution"].append(shield_exec_record)
        self._in_shield_phase = False
        self._flush_pending_barrier_status_triggers(char_manager, result)

    def _execute_spirit(self, char_manager: Any, ally_chars: List[Any], result: Dict[str, Any]):
        """执行灵力效果（触发boost相关buff + 扣除灵力）

        规则：
        - 输入 spirit_level=0：直接跳过（不触发buff、也不扣灵力）
        - 若当前灵力不足：实际执行等级 actual_level = min(spirit_level, floor(current_spirit))
          例如 current=1.2, level=3 -> actual=1，扣除后剩 0.2
        - 后续 buff 触发次数按 actual_level 计算
        - boost_target 口径调整：2=自身、1=己方全体、0=无（跳过后续buff阶段）
        - boost_buff(=boost_type) 为触发的 sub_id：映射 n -> [1,n,target,1,1]
        """
        for front_pos in [0, 1, 2]:
            spirit_exec_record = {
                "char_pos": front_pos,
                "status": "success",
                "reason": "",
                "requested_level": 0,
                "actual_level": 0,
                "buff_trigger_times": 0,
                "boost_target_raw": 0,
                "target_type": 0,
                "boost_type": 0,
                "original_spirit": 0.0,
                "final_spirit": 0.0,
            }

            try:
                char = char_manager.get_character_instance("我方前排", front_pos)
                if not char:
                    spirit_exec_record["status"] = "skipped"
                    spirit_exec_record["reason"] = "角色不存在"
                    result["spirit_execution"].append(spirit_exec_record)
                    continue

                # 1) 获取配置：请求的灵力等级
                op_status = self.get_op_status(front_pos)
                requested_level = int(getattr(op_status, "spirit_level", 0))
                spirit_exec_record["requested_level"] = requested_level
                spirit_exec_record["original_spirit"] = float(getattr(char, "spirit", 0.0))
                op_status.pre_spirit_value = float(getattr(char, "spirit", 0.0))
                op_status = self.get_op_status(front_pos)
                
                if requested_level <= 0:
                    spirit_exec_record["reason"] = "灵力等级为0，跳过"
                    spirit_exec_record["final_spirit"] = float(getattr(char, "spirit", 0.0))
                    result["spirit_execution"].append(spirit_exec_record)
                    continue

                # 2) 计算实际可执行等级：按 floor(current_spirit)
                current_spirit = float(getattr(char, "spirit", 0.0))
                actual_level = min(requested_level, int(current_spirit))
                spirit_exec_record["actual_level"] = actual_level
                spirit_exec_record["buff_trigger_times"] = actual_level
                self.get_op_status(front_pos).spirit_level = actual_level
                
                if actual_level <= 0:
                    spirit_exec_record["reason"] = f"灵力不足（current={current_spirit}），实际执行等级=0，跳过"
                    spirit_exec_record["final_spirit"] = float(getattr(char, "spirit", 0.0))
                    result["spirit_execution"].append(spirit_exec_record)
                    continue

                # 3) 读取 boost_target / boost_buff（spirit触发buff类型参考）
                boost_target_raw = int(getattr(char.stats, "boost_target", 0))
                spirit_exec_record["boost_target_raw"] = boost_target_raw
                if boost_target_raw == 0:
                    # 没有spirit buff，仅扣灵力
                    new_spirit = max(0.0, current_spirit - actual_level)
                    char_manager.update_character_spirit("我方前排", front_pos, new_spirit, "set")
                    spirit_exec_record["final_spirit"] = float(getattr(char, "spirit", 0.0))
                    spirit_exec_record["reason"] = f"boost_target=0（无spirit buff），仅扣除灵力{actual_level}（{current_spirit}->{spirit_exec_record['final_spirit']})"
                    result["spirit_execution"].append(spirit_exec_record)
                    continue
                if boost_target_raw not in (1, 2):
                    raise ValueError(f"无效的灵力目标类型：{boost_target_raw}（仅支持0/1/2，其中2=自身，1=己方全体，0=无）")

                # 映射到 _apply_buff_effect：1=自身、2=己方全体
                mapped_target_type = 1 if boost_target_raw == 2 else 2
                spirit_exec_record["target_type"] = mapped_target_type

                boost_type = int(getattr(char.stats, "boost_buff", 0))
                spirit_exec_record["boost_type"] = boost_type
                if boost_type == 0:
                    # 没有spirit buff，仅扣灵力
                    new_spirit = max(0.0, current_spirit - actual_level)
                    char_manager.update_character_spirit("我方前排", front_pos, new_spirit, "set")
                    spirit_exec_record["final_spirit"] = float(getattr(char, "spirit", 0.0))
                    spirit_exec_record["reason"] = f"boost_buff=0（无spirit buff），仅扣除灵力{actual_level}（{current_spirit}->{spirit_exec_record['final_spirit']})"
                    result["spirit_execution"].append(spirit_exec_record)
                    continue

                # 4) 触发 buff：次数=actual_level，映射 n -> [1,n,target,1,1]
                for _ in range(actual_level):
                    buff_effect = [1, boost_type, mapped_target_type, 1, 1]
                    self._apply_buff_effect(
                        effect_list=buff_effect,
                        char_manager=char_manager,
                        attacker_pos_idx=front_pos,
                        enemy_target_pos_idx=self.get_enemy_target_pos(front_pos),
                    )

                # 5) 扣除灵力：减少 actual_level（保留小数部分）
                new_spirit = max(0.0, current_spirit - actual_level)
                char_manager.update_character_spirit("我方前排", front_pos, new_spirit, "set")
                spirit_exec_record["final_spirit"] = float(getattr(char, "spirit", 0.0))

                spirit_exec_record["reason"] = (
                    f"请求等级={requested_level}，实际执行={actual_level}；"
                    f"触发{actual_level}次buff（sub_id={boost_type}, target={mapped_target_type}），"
                    f"灵力{current_spirit}->{spirit_exec_record['final_spirit']}"
                )

            except Exception as e:
                spirit_exec_record["status"] = "error"
                spirit_exec_record["reason"] = str(e)
                result["errors"].append(f"灵力处理失败（角色{front_pos}）：{str(e)}")

            result["spirit_execution"].append(spirit_exec_record)

    def execute_pre_attack_buffs_for_attacker(
        self,
        char_manager: Any,
        attacker_pos: int,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """仅对一个出手者执行 attack_type 对应的 effect_before。"""
        pre_attack_record = {
            "char_pos": attacker_pos,
            "status": "success",
            "reason": "",
            "attack_type": "",
            "effect_before_count": 0,
            "applied_buff_count": 0,
        }
        try:
            char = char_manager.get_character_instance("我方前排", attacker_pos)
            if not char:
                pre_attack_record["status"] = "skipped"
                pre_attack_record["reason"] = "角色不存在"
                result["pre_attack_buff_execution"].append(pre_attack_record)
                return pre_attack_record

            op_status = self.get_op_status(attacker_pos)
            attack_type = op_status.attack_type
            pre_attack_record["attack_type"] = attack_type

            if attack_type not in char.attack_skills:
                raise ValueError(f"角色{attacker_pos}号位无{attack_type}类型的攻击技能")

            attack_skill_data = char.attack_skills[attack_type]
            effect_before = attack_skill_data.get("global_attributes", {}).get("effect_before", [])
            pre_attack_record["effect_before_count"] = len(effect_before)
            if not effect_before:
                pre_attack_record["reason"] = "无攻击前效果需要处理"
                result["pre_attack_buff_execution"].append(pre_attack_record)
                return pre_attack_record

            applied_count = 0
            for effect in effect_before:
                try:
                    applied = self._apply_buff_effect(
                        effect_list=effect,
                        char_manager=char_manager,
                        attacker_pos_idx=attacker_pos,
                        enemy_target_pos_idx=self.get_enemy_target_pos(attacker_pos),
                    )
                    applied_count += int(applied)
                except Exception as e:
                    result["errors"].append(
                        f"攻击前Buff处理失败（角色{attacker_pos}，效果{effect}）：{str(e)}"
                    )

            pre_attack_record["applied_buff_count"] = applied_count
            pre_attack_record["reason"] = f"成功应用{applied_count}次（来源effect_before条数={len(effect_before)}）"
            result["pre_attack_buff_execution"].append(pre_attack_record)
            return pre_attack_record

        except Exception as e:
            pre_attack_record["status"] = "error"
            pre_attack_record["reason"] = str(e)
            result["errors"].append(f"攻击前Buff处理失败（角色{attacker_pos}）：{str(e)}")
            # 新增：打印完整堆栈（定位是哪一行在做 str + list）
            result["errors"].append(traceback.format_exc())
            result["pre_attack_buff_execution"].append(pre_attack_record)
            return pre_attack_record
        
    def execute_post_attack_buffs_for_attacker(
        self,
        char_manager: Any,
        attacker_pos: int,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """仅对一个出手者执行 attack_type 对应的 effect_after（攻击后效果）。"""
        post_attack_record = {
            "char_pos": attacker_pos,
            "status": "success",
            "reason": "",
            "attack_type": "",
            "effect_after_count": 0,
            "applied_buff_count": 0,
        }

        try:
            char = char_manager.get_character_instance("我方前排", attacker_pos)
            if not char:
                post_attack_record["status"] = "skipped"
                post_attack_record["reason"] = "角色不存在"
                result["post_attack_buff_execution"].append(post_attack_record)
                return post_attack_record

            op_status = self.get_op_status(attacker_pos)
            attack_type = op_status.attack_type
            post_attack_record["attack_type"] = attack_type

            if attack_type not in char.attack_skills:
                raise ValueError(f"角色{attacker_pos}号位无{attack_type}类型的攻击技能")

            attack_skill_data = char.attack_skills[attack_type]
            effect_after = attack_skill_data.get("global_attributes", {}).get("effect_after", [])
            post_attack_record["effect_after_count"] = len(effect_after)

            if not effect_after:
                post_attack_record["reason"] = "无攻击后效果需要处理"
                result["post_attack_buff_execution"].append(post_attack_record)
                return post_attack_record

            applied_count = 0
            for effect in effect_after:
                try:
                    applied = self._apply_buff_effect(
                        effect_list=effect,
                        char_manager=char_manager,
                        attacker_pos_idx=attacker_pos,
                        enemy_target_pos_idx=self.get_enemy_target_pos(attacker_pos),
                    )
                    # 用实际生效次数累计（全体/异常等会 >1）
                    applied_count += int(applied)
                except Exception as e:
                    result["errors"].append(
                        f"攻击后Buff处理失败（角色{attacker_pos}，效果{effect}）：{str(e)}"
                    )

            post_attack_record["applied_buff_count"] = applied_count
            post_attack_record["reason"] = f"成功应用{applied_count}次（来源effect_after条数={len(effect_after)}）"
            result["post_attack_buff_execution"].append(post_attack_record)
            return post_attack_record

        except Exception as e:
            post_attack_record["status"] = "error"
            post_attack_record["reason"] = str(e)
            result["errors"].append(f"攻击后Buff处理失败（角色{attacker_pos}）：{str(e)}")
            result["post_attack_buff_execution"].append(post_attack_record)
            return post_attack_record
