from __future__ import annotations

from typing import Dict, Set


DEFAULT_ENEMY_ID = 1001
DEFAULT_ALLY_ID = 1003
DEFAULT_ATTACK_TYPE = "5"
DEFAULT_SPIRIT_LEVEL = 3
DEFAULT_TARGET_ENEMY_POS = 0
DEFAULT_SHIELD_OPEN_COUNT = 3

QUALITY_LABELS = ["日", "月", "火", "水", "木", "金", "土", "星", "无"]
QUALITY_STATE_TEXT = {0: "弱", 1: "普", 2: "抗"}
QUALITY_DEFAULT = [1, 1, 1, 1, 1, 1, 1, 1, 1]

TYPE_LABELS = {
    1: "防御",
    2: "支援",
    3: "回复",
    4: "干扰",
    5: "攻击",
    6: "技巧",
    7: "速攻",
    8: "破坏",
}

ELEMENT_RAW_LABELS = {
    0: "无",
    1: "日",
    2: "月",
    3: "火",
    4: "水",
    5: "木",
    6: "金",
    7: "土",
    8: "星",
    9: "无",
}

ELEMENT_BUFF_SUBID_LABELS = {
    1: "日属性",
    2: "月属性",
    3: "火属性",
    4: "水属性",
    5: "木属性",
    6: "金属性",
    7: "土属性",
    8: "星属性",
    9: "无属性",
}

ELEMENT_RAW_TO_BUFF_SUBID = {
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    6: 6,
    7: 7,
    8: 8,
    9: 9,
}

BULLET_RAW_LABELS = {
    0: "未定义",
    1: "通常弹",
    2: "镭射弹",
    3: "体术弹",
    4: "斩击弹",
    5: "动能弹",
    6: "流体弹",
    7: "能量弹",
    8: "御符弹",
    9: "光弹",
    10: "尖弹",
    11: "追踪弹",
}

BULLET_BUFF_SUBID_LABELS = {
    1: "通常弹",
    2: "镭射弹",
    3: "体术弹",
    4: "斩击弹",
    5: "动能弹",
    6: "流体弹",
    7: "能量弹",
    8: "御符弹",
    9: "光弹",
    10: "尖弹",
    11: "追踪弹",
}

BULLET_RAW_TO_BUFF_SUBID = {
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    6: 6,
    7: 7,
    8: 8,
    9: 9,
    10: 10,
    11: 11,
}


def normalized_lookup_keys(raw_value: int, mapping: Dict[int, int]) -> Set[int]:
    raw = int(raw_value)
    keys = {raw}
    mapped = mapping.get(raw)
    if mapped is not None:
        keys.add(int(mapped))
    return keys
