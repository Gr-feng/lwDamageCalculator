import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Union


# =========================
# Data models
# =========================

@dataclass
class Skill:
    """技能数据结构（包含冷却管理）"""
    skill_id: int
    name: str
    a: List[int]
    b: List[int]
    c: List[int]
    cd: int
    cur_cd: int = 0


@dataclass
class Stats:
    """角色当前战斗属性状态"""
    hp: int
    yang_atk: int
    yang_def: int
    yin_atk: int
    yin_def: int
    spd: int

    advantage_attack: int = 0
    advantage_resist: int = 0
    disadvantage_attack: int = 0
    disadvantage_resist: int = 0

    barrier_status_1: int = 0
    barrier_status_2: int = 0
    barrier_status_3: int = 0
    barrier_status_4: int = 0
    barrier_status_5: int = 0

    boost_buff: int = 0
    boost_target: int = 0
    graze_buff: int = 0
    graze_target: int = 1

    # quality: 10位list，对应 1占位 + 8属性 + 无属性(默认1)
    quality: List[int] = field(default_factory=lambda: [1] * 10)


@dataclass
class Buff:
    """简化版 Buff / DeBuff"""
    buff_id: int
    sub_id: int = 0
    duration: int = 0
    value: float = 0.0


@dataclass
class Barrier:
    """简化版护盾/结界"""
    barrier_id: int
    type: int = 0
    is_active: bool = True


@dataclass
class CharacterInstance:
    """单个角色实例"""

    # —— 必填 ——
    character_info: Dict[str, Any]
    attack_skills: Dict[str, Any]
    stats: Stats

    # —— 默认 ——
    skills: List[Skill] = field(default_factory=list)
    chain_character: List[int] = field(default_factory=list)

    buffs: List[Buff] = field(default_factory=list)
    barriers: List[Barrier] = field(default_factory=list)

    # 段落内执行标记：固定 6 段
    paragraph_executed: List[bool] = field(default_factory=lambda: [False] * 6)

    spirit: float = 1.0

    is_stunned: bool = False

    # 全破标记（护盾全部 inactive 时为 True；恢复任意护盾后会自动清 False）
    is_break_all: bool = False

    # =========================
    # spirit 相关
    # =========================
    def update_spirit(self, value: float, mode: Literal["set", "add"] = "set") -> float:
        """修改角色 spirit（限制 0~5）"""
        if mode == "set":
            self.spirit = max(0.0, min(5.0, float(value)))
        elif mode == "add":
            self.spirit = max(0.0, min(5.0, self.spirit + float(value)))
        return self.spirit

    # =========================
    # barrier 相关
    # =========================
    def add_barrier(self, num: int) -> int:
        """恢复护盾：从后往前把 inactive 改为 active，同时把 type 改成 0"""
        if num <= 0 or not self.barriers:
            return 0

        inactive = [b for b in reversed(self.barriers) if not b.is_active]
        restore_count = min(num, len(inactive))
        for i in range(restore_count):
            inactive[i].is_active = True
            inactive[i].type = 0

        # 只要恢复了任意护盾，就不再处于全破状态
        if restore_count > 0:
            self.is_break_all = False
        return restore_count

    def break_all_barrier(self):
        """全破：清空buff，设置 is_break_all=True，并写入全破固定两个buff"""
        self.buffs.clear()
        self.is_break_all = True
        # 追加两个固定 buff
        self.buffs.append(Buff(buff_id=1, sub_id=2, duration=1, value=-10))
        self.buffs.append(Buff(buff_id=1, sub_id=4, duration=1, value=-10))

    def break_barrier(self, barrier_type: int) -> int:
        """护盾击破：
        - barrier_type == 0：击破 1 个激活的
        - barrier_type != 0：击破对应类型所有激活护盾
        击破后若判定所有护盾都 inactive，则触发 break_all_barrier

        细节：击破任意护盾后，将该护盾 type 置为 0。
        """
        if not self.barriers:
            self.is_break_all = False
            return 0

        broken = 0
        # 属性破盾（单破）
        if barrier_type == 0:
            for b in self.barriers:
                if b.is_active:
                    b.is_active = False
                    b.type = 0
                    broken = 1
                    break
        # 异常破盾（同类型全破）
        else:
            for b in self.barriers:
                if b.is_active and b.type == barrier_type:
                    b.is_active = False
                    b.type = 0
                    broken += 1

        all_inactive = all(not b.is_active for b in self.barriers) if self.barriers else False
        if all_inactive:
            # 只有从非全破 -> 全破时才触发全破效果
            if not self.is_break_all:
                self.break_all_barrier()
            self.is_break_all = True
        else:
            self.is_break_all = False
        return broken

    def set_barrier_type(self, n: int, barrier_type: int) -> int:
        """从前往后检索：把 active 且 type==0 的护盾改成 barrier_type，最多改 n 个。
        返回实际修改数量。
        """
        if n <= 0 or not self.barriers:
            return 0
        if barrier_type < 0:
            raise ValueError("barrier_type 必须是非负整数")

        changed = 0
        for b in self.barriers:
            if changed >= n:
                break
            if b.is_active and b.type == 0:
                b.type = int(barrier_type)
                changed += 1
        return changed

    # =========================
    # skill 相关
    # =========================
    def use_skill(self, skill_id: int) -> Optional[Dict[str, List[int]]]:
        """释放技能：在冷却则返回 None，否则进入冷却并返回效果"""
        target = None
        for s in self.skills:
            if s.skill_id == skill_id:
                target = s
                break
        if target is None:
            raise ValueError(f"角色无ID为{skill_id}的技能")
        if target.cur_cd > 0:
            return None
        target.cur_cd = target.cd
        return {"a": target.a, "b": target.b, "c": target.c}

    def tick_skill_cd(self):
        """推进技能冷却（回合推进）"""
        for s in self.skills:
            if s.cur_cd > 0:
                s.cur_cd -= 1

    # =========================
    # hp 相关
    # =========================
    def damage(self, damage: int) -> bool:
        """扣血，返回是否死亡"""
        if damage < 0:
            raise ValueError("扣血量必须为正数")
        self.stats.hp = max(0, self.stats.hp - damage)
        return self.stats.hp <= 0

    # =========================
    # paragraph_executed 相关
    # =========================
    def get_paragraph_executed(self, idx: int) -> bool:
        """idx: 0~5"""
        if idx < 0 or idx >= 6:
            raise ValueError("段落索引必须是 0~5")
        return bool(self.paragraph_executed[idx])

    def set_paragraph_executed(self, idx: int):
        """idx: 0~5 置 True；idx=6 重置所有为 False"""
        if idx == 6:
            for i in range(6):
                self.paragraph_executed[i] = False
            return
        if idx < 0 or idx >= 6:
            raise ValueError("段落索引必须是 0~5，或 6 表示 reset")
        self.paragraph_executed[idx] = True


# =========================
# CharacterInstanceManager
# =========================

class CharacterInstanceManager:
    """角色实例管理器（敌方3/我方前排3/我方后排3）"""

    # ====================== 内部工具 ======================
    def __init__(self):
        self.instances: Dict[str, List[Optional[CharacterInstance]]] = {
            "敌方": [None, None, None],
            "我方前排": [None, None, None],
            "我方后排": [None, None, None],
        }
        # 我方位置映射：0-2=前排，3-5=后排
        self.ally_position_map = {
            0: ("我方前排", 0),
            1: ("我方前排", 1),
            2: ("我方前排", 2),
            3: ("我方后排", 0),
            4: ("我方后排", 1),
            5: ("我方后排", 2),
        }

    def _norm_pos_0_2(self, position: int) -> int:
        """严格使用 0~2（不再兼容旧 1~3，避免混乱）"""
        if position not in (0, 1, 2):
            raise ValueError("位置必须是 0~2")
        return position

    def _parse_quality(self, quality_str: Any) -> List[int]:
        """
        将原始 quality 字符串解析为长度10的列表：
        [占位, 属性1, 属性2, ..., 属性8, 无属性]

        例如：
        "21011120" -> [1,2,1,0,1,1,1,2,0,1]

        其中：
        - 0：弱点
        - 1：普通
        - 2：抗性
        - 第0位为占位
        - 最后一位为无属性，默认1
        """
        s = str(quality_str) if quality_str is not None else ""
        digits = [int(ch) for ch in s if ch.isdigit()]
        digits = ([1] * 9 + digits)[-9:]
        digits.append(1)
        return digits

    def _parse_skills(self, raw_skills: List[Dict[str, Any]]) -> List[Skill]:
        parsed: List[Skill] = []
        for raw in raw_skills:
            parsed.append(
                Skill(
                    skill_id=int(raw.get("id", 0)),
                    name=str(raw.get("name", "")),
                    a=list(raw.get("a", [])),
                    b=list(raw.get("b", [])),
                    c=list(raw.get("c", [])),
                    cd=int(raw.get("cd", 0)),
                    cur_cd=0,
                )
            )
        return parsed

    def _create_character_instance(self, char_data: Dict[str, Any], default_barrier_count: int = 0) -> CharacterInstance:
        char_info = char_data["character_info"]

        stats = Stats(
            hp=int(char_info.get("hp", 0)),
            yang_atk=int(char_info.get("yang_atk", 0)),
            yang_def=int(char_info.get("yang_def", 0)),
            yin_atk=int(char_info.get("yin_atk", 0)),
            yin_def=int(char_info.get("yin_def", 0)),
            spd=int(char_info.get("speed", 0)),
            advantage_attack=int(char_info.get("advantage_attack", 0)),
            advantage_resist=int(char_info.get("advantage_resist", 0)),
            disadvantage_attack=int(char_info.get("disadvantage_attack", 0)),
            disadvantage_resist=int(char_info.get("disadvantage_resist", 0)),
            barrier_status_1=int(char_info.get("barrier_status_1", 0)),
            barrier_status_2=int(char_info.get("barrier_status_2", 0)),
            barrier_status_3=int(char_info.get("barrier_status_3", 0)),
            barrier_status_4=int(char_info.get("barrier_status_4", 0)),
            barrier_status_5=int(char_info.get("barrier_status_5", 0)),
            boost_buff=int(char_info.get("boost_buff", 0)),
            boost_target=int(char_info.get("boost_target", 0)),
            graze_buff=int(char_info.get("graze_buff", 0)),
            graze_target=int(char_info.get("graze_target", 0)),
            quality=self._parse_quality(char_info.get("quality", "")),
        )

        inst = CharacterInstance(
            character_info=char_info,
            attack_skills=char_data.get("attack_skills", {}) or {},
            skills=self._parse_skills(char_data.get("skills", []) or []),
            chain_character=list(char_data.get("chain_character", []) or []),
            stats=stats,
            buffs=[],
            barriers=[],
            paragraph_executed=[False] * 6,
            spirit=1.0,
            is_stunned=False,
            is_break_all=False,
        )

        if default_barrier_count > 0:
            # 默认护盾：初始 type 全部为 0
            inst.barriers = [
                Barrier(barrier_id=i + 1, type=0, is_active=True)
                for i in range(default_barrier_count)
            ]

        return inst

    def load_character_data(self, character_id: int, data_dir: str = "datajson") -> dict:
        path = os.path.join(data_dir, f"{character_id}.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ====================== 创建角色相关 ======================
    def add_enemy_by_id(
        self,
        position: int,
        character_id: int,
        data_dir: str = "datajson",
        yang_def_override: Optional[float] = None,
        yin_def_override: Optional[float] = None,
        hp_override: Optional[int] = None,
        barrier_count: int = 5,
    ):
        data = self.load_character_data(character_id, data_dir=data_dir)
        custom: Dict[str, Any] = {}
        if yang_def_override is not None:
            custom["yang_def"] = yang_def_override
        if yin_def_override is not None:
            custom["yin_def"] = yin_def_override
        if hp_override is not None:
            custom["hp"] = hp_override
        self.add_enemy_character(position=position, char_data=data, custom_attrs=custom or None, barrier_count=barrier_count)

    def add_ally_by_id(self, position: int, character_id: int, data_dir: str = "datajson"):
        data = self.load_character_data(character_id, data_dir=data_dir)
        self.add_ally_character(position=position, char_data=data)

    def add_enemy_character(
        self,
        position: int,
        char_data: Dict[str, Any],
        custom_attrs: Optional[Dict[str, Any]] = None,
        barrier_count: int = 5,
    ):
        """添加敌方角色：position 必须是 0~2；默认 5 盾"""
        idx = self._norm_pos_0_2(position)
        inst = self._create_character_instance(char_data, default_barrier_count=0)

        # 应用 custom_attrs
        if custom_attrs:
            for k, v in custom_attrs.items():
                if hasattr(inst.stats, k):
                    setattr(inst.stats, k, v)
                elif k == "spirit":
                    inst.update_spirit(float(v), "set")
                else:
                    raise AttributeError(f"Stats 无字段 {k}")

        # 敌方默认 5 盾（传入 <=0 则不加）
        if barrier_count > 0:
            # 敌方护盾初始 type 全部为 0
            inst.barriers = [
                Barrier(barrier_id=i + 1, type=0, is_active=True)
                for i in range(barrier_count)
            ]
        else:
            inst.barriers = []

        inst.is_break_all = all(not b.is_active for b in inst.barriers) if inst.barriers else False
        self.instances["敌方"][idx] = inst

    def add_ally_character(self, position: int, char_data: Dict[str, Any]):
        """添加我方角色：position 0-2前排，3-5后排；默认 6 盾"""
        if position not in self.ally_position_map:
            raise ValueError(f"我方位置编码错误，可选值：{list(self.ally_position_map.keys())}")
        team_type, idx = self.ally_position_map[position]
        self.instances[team_type][idx] = self._create_character_instance(char_data, default_barrier_count=6)

    def swap_ally_front_back(self, position: int):
        """交换我方前后排角色：position 0~2"""
        idx = self._norm_pos_0_2(position)
        self.instances["我方前排"][idx], self.instances["我方后排"][idx] = self.instances["我方后排"][idx], self.instances["我方前排"][idx]

    def get_character_instance(self, team_type: str, position: int) -> Optional[CharacterInstance]:
        """获取角色实例：position 0~2"""
        if team_type not in self.instances:
            raise ValueError(f"队伍类型错误，可选值：{list(self.instances.keys())}")
        idx = self._norm_pos_0_2(position)
        return self.instances[team_type][idx]

    # ====================== 面板属性相关 ======================
    def update_character_stats(self, team_type: str, position: int, **attrs):
        inst = self.get_character_instance(team_type, position)
        if not inst:
            raise ValueError(f"{team_type} 位置{position}无角色")

        for k, v in attrs.items():
            if hasattr(inst.stats, k):
                setattr(inst.stats, k, v)
            elif k == "spirit":
                inst.update_spirit(float(v), "set")
            else:
                raise AttributeError(f"Stats 无字段 {k}")

    def damage_and_remove_character(self, team_type: str, position: int, damage: int) -> bool:
        inst = self.get_character_instance(team_type, position)
        if not inst:
            return False
        dead = inst.damage(damage)
        if dead:
            idx = self._norm_pos_0_2(position)
            self.instances[team_type][idx] = None
        return dead

    def reset_character_status(self, team_type: str, position: int):
        """重置角色状态：
        - 技能 cd 置 0
        - spirit=1
        - 清空 buffs
        - 护盾：从后往前把所有护盾设为 active=True, type=0（不足则补到默认数量）
        - paragraph_executed 全部 False
        """
        inst = self.get_character_instance(team_type, position)
        if not inst:
            raise ValueError(f"{team_type}位置{position}无角色")

        char_info = inst.character_info
        inst.stats = Stats(
            hp=int(char_info.get("hp", 0)),
            yang_atk=int(char_info.get("yang_atk", 0)),
            yang_def=int(char_info.get("yang_def", 0)),
            yin_atk=int(char_info.get("yin_atk", 0)),
            yin_def=int(char_info.get("yin_def", 0)),
            spd=int(char_info.get("speed", 0)),
            advantage_attack=int(char_info.get("advantage_attack", 0)),
            advantage_resist=int(char_info.get("advantage_resist", 0)),
            disadvantage_attack=int(char_info.get("disadvantage_attack", 0)),
            disadvantage_resist=int(char_info.get("disadvantage_resist", 0)),
            barrier_status_1=int(char_info.get("barrier_status_1", 0)),
            barrier_status_2=int(char_info.get("barrier_status_2", 0)),
            barrier_status_3=int(char_info.get("barrier_status_3", 0)),
            barrier_status_4=int(char_info.get("barrier_status_4", 0)),
            barrier_status_5=int(char_info.get("barrier_status_5", 0)),
            boost_buff=int(char_info.get("boost_buff", 0)),
            boost_target=int(char_info.get("boost_target", 0)),
            graze_buff=int(char_info.get("graze_buff", 0)),
            graze_target=int(char_info.get("graze_target", 0)),
            quality=self._parse_quality(char_info.get("quality", "")),
        )

        for s in inst.skills:
            s.cur_cd = 0

        inst.spirit = 1.0
        inst.buffs.clear()

        # 护盾恢复逻辑：从后往前把所有护盾设为 active=True, type=0；不足补齐
        default_cnt = 6 if team_type in ("我方前排", "我方后排") else 5
        if len(inst.barriers) < default_cnt:
            # 补齐到默认数量
            start = len(inst.barriers)
            for i in range(start, default_cnt):
                inst.barriers.append(Barrier(barrier_id=i + 1, type=0, is_active=True))
        # 从后往前 reset
        for b in reversed(inst.barriers):
            b.is_active = True
            b.type = 0

        inst.is_break_all = False
        inst.is_stunned = False

        inst.paragraph_executed = [False] * 6

    # ====================== paragraph_executed 相关 ======================
    def get_paragraph_executed(self, team_type: str, position: int, idx: int) -> bool:
        inst = self.get_character_instance(team_type, position)
        if not inst:
            raise ValueError(f"{team_type} 位置{position}无角色")
        return inst.get_paragraph_executed(idx)

    def set_paragraph_executed(self, team_type: str, position: int, idx: int):
        inst = self.get_character_instance(team_type, position)
        if not inst:
            raise ValueError(f"{team_type} 位置{position}无角色")
        inst.set_paragraph_executed(idx)

    # ====================== Buff相关 ======================
    def add_character_buff(self, team_type: str, position: int, buff_id: int, sub_id: int, duration: int, value: float):
        inst = self.get_character_instance(team_type, position)
        if not inst:
            raise ValueError(f"{team_type} 位置{position}无角色")

        # ID==1 或 41：value 必须限制在 [-10, 10]
        def clamp(v: float) -> float:
            return max(-10.0, min(10.0, float(v)))

        if buff_id in (1, 41):
            value = clamp(value)

        # 先检索同ID+subid
        for b in inst.buffs:
            if b.buff_id == buff_id and b.sub_id == sub_id:
                b.duration = max(int(b.duration), int(duration))
                if buff_id in (1, 41):
                    b.value = clamp(b.value + float(value))
                # 不是 1/41：保持原 value
                return

        # 不存在则新增
        inst.buffs.append(Buff(buff_id=int(buff_id), sub_id=int(sub_id), duration=int(duration), value=float(value)))

    # ====================== Skill相关 ======================
    def get_character_skill(self, team_type: str, position: int, skill_id: Union[int, str]) -> Optional[Union[Skill, Dict[str, Any]]]:
        inst = self.get_character_instance(team_type, position)
        if not inst:
            return None

        sid = int(skill_id)
        for s in inst.skills:
            if s.skill_id == sid:
                return s

        # 攻击技能表
        if str(skill_id) in inst.attack_skills:
            return inst.attack_skills[str(skill_id)]

        return None

    def use_character_skill(self, team_type: str, position: int, skill_id: int) -> Optional[Dict[str, List[int]]]:
        inst = self.get_character_instance(team_type, position)
        if not inst:
            return None
        return inst.use_skill(int(skill_id))

    def tick_character_skill_cd(self, team_type: str, position: int):
        inst = self.get_character_instance(team_type, position)
        if not inst:
            return
        inst.tick_skill_cd()

    # ====================== Spirit相关 ======================
    def update_character_spirit(self, team_type: str, position: int, value: float, mode: Literal["set", "add"] = "set") -> Optional[float]:
        inst = self.get_character_instance(team_type, position)
        if not inst:
            return None
        return inst.update_spirit(float(value), mode)

    # ====================== Barrier相关 ======================
    def add_character_barrier(self, team_type: str, position: int, num: int) -> Optional[int]:
        inst = self.get_character_instance(team_type, position)
        if not inst:
            return None
        return inst.add_barrier(int(num))

    def set_character_barrier_type(self, team_type: str, position: int, n: int, barrier_type: int) -> Optional[int]:
        """修改护盾 type：从前往后把 active 且 type==0 的护盾改成 barrier_type，最多 n 个。"""
        inst = self.get_character_instance(team_type, position)
        if not inst:
            return None
        return inst.set_barrier_type(int(n), int(barrier_type))

    def break_character_barrier(self, team_type: str, position: int, barrier_type: int) -> Optional[int]:
        inst = self.get_character_instance(team_type, position)
        if not inst:
            return None
        return inst.break_barrier(int(barrier_type))
