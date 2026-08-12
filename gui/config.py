from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from backend.core.combat_constants import (
    DEFAULT_ALLY_ID,
    DEFAULT_ATTACK_TYPE,
    DEFAULT_ENEMY_ID,
    DEFAULT_SHIELD_OPEN_COUNT,
    DEFAULT_SPIRIT_LEVEL,
    DEFAULT_TARGET_ENEMY_POS,
    QUALITY_DEFAULT,
)


EQUIPMENT_SLOT_KEYS = ("1a", "2a", "1b", "2b", "5")
LEGACY_EQUIPMENT_KEY_MIGRATION = {
    "1": "1a",
    "2": "2a",
    "1c": "1b",
    "2c": "2b",
    "5": "5",
}


def default_equipment_ids() -> Dict[str, int]:
    return {key: 0 for key in EQUIPMENT_SLOT_KEYS}


@dataclass
class EnemySlotConfig:
    enabled: bool = False
    character_id: int = DEFAULT_ENEMY_ID
    hp: int = 50_000_000
    yang_atk: int = 0
    yang_def: int = 10_000
    yin_atk: int = 0
    yin_def: int = 10_000
    speed: int = 0
    barrier_count: int = 9
    barrier_types: List[int] = field(default_factory=list)
    quality: List[int] = field(default_factory=lambda: list(QUALITY_DEFAULT))
    tribe_text: str = ""
    is_break_all: bool = False
    buffs: List[List[int]] = field(default_factory=list)
    enemy_skill_effects: List[List[int]] = field(default_factory=list)


@dataclass
class AllySlotConfig:
    enabled: bool = False
    character_id: int = DEFAULT_ALLY_ID
    initial_spirit: float = 3.0
    barrier_count: int = 5
    barrier_types: List[int] = field(default_factory=list)
    skill_order_text: str = "0,1,2"
    shield_open_count: int = DEFAULT_SHIELD_OPEN_COUNT
    attack_type: str = DEFAULT_ATTACK_TYPE
    spirit_level: int = DEFAULT_SPIRIT_LEVEL
    target_enemy_pos: int = DEFAULT_TARGET_ENEMY_POS
    buffs: List[List[int]] = field(default_factory=list)
    equipment_ids: Dict[str, int] = field(default_factory=default_equipment_ids)

    def __post_init__(self):
        merged = default_equipment_ids()
        raw = self.equipment_ids or {}
        if isinstance(raw, dict):
            for key, value in raw.items():
                normalized_key = str(key)
                if normalized_key not in merged:
                    normalized_key = LEGACY_EQUIPMENT_KEY_MIGRATION.get(normalized_key, normalized_key)
                if normalized_key not in merged:
                    continue
                try:
                    merged[normalized_key] = int(value)
                except Exception:
                    merged[normalized_key] = 0
        self.equipment_ids = merged


@dataclass
class FieldBuffConfig:
    bullet_type_modifiers: List[List[float]] = field(default_factory=list)
    element_modifiers: List[List[float]] = field(default_factory=list)
    type_resist_modifiers: List[List[float]] = field(default_factory=list)
    vs_tags: List[str] = field(default_factory=list)
    arena_type_boosts: List[int] = field(default_factory=list)
    arena_yinyang: str = "yang"
    realistic: bool = False
    vs_tag_effects: List[Dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def _normalize_rows(rows: List[List[Any]]) -> List[List[float]]:
        normalized: List[List[float]] = []
        for row in rows or []:
            if not isinstance(row, list) or len(row) < 2:
                continue
            try:
                normalized.append([int(row[0]), float(row[1])])
            except Exception:
                continue
        return normalized

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "FieldBuffConfig":
        payload = payload or {}
        return cls(
            bullet_type_modifiers=cls._normalize_rows(payload.get("bullet_type_modifiers", [])),
            element_modifiers=cls._normalize_rows(payload.get("element_modifiers", [])),
            type_resist_modifiers=cls._normalize_rows(payload.get("type_resist_modifiers", [])),
            vs_tags=[str(v) for v in (payload.get("vs_tags") or []) if str(v)],
            arena_type_boosts=[
                int(v)
                for v in (payload.get("arena_type_boosts") or [])
                if str(v).strip().isdigit()
            ][:2],
            arena_yinyang=str(payload.get("arena_yinyang", "yang") or "yang"),
            realistic=bool(payload.get("realistic", False)),
            vs_tag_effects=[row for row in (payload.get("vs_tag_effects") or []) if isinstance(row, dict)],
        )

    @staticmethod
    def _to_runtime_group(rows: List[List[float]]) -> Dict[int, float]:
        group: Dict[int, float] = {}
        for sub_id, value in rows:
            key = int(sub_id)
            factor = float(value) / 100.0
            group[key] = group.get(key, 1.0) * factor
        return group

    def to_runtime_dict(self) -> Dict[str, Dict[int, float]]:
        runtime = {
            "bullet_type": self._to_runtime_group(self.bullet_type_modifiers),
            "element": self._to_runtime_group(self.element_modifiers),
            "type_resist": self._to_runtime_group(self.type_resist_modifiers),
            "killer_crit_bonus": {},
        }
        for effect in self.vs_tag_effects or []:
            try:
                side = int(effect.get("side", 0) or 0)
                kind = int(effect.get("kind", 0) or 0)
                sub_id = int(effect.get("sub_id", 0) or 0)
                factor = 1.0 + float(effect.get("value", 0) or 0.0) / 100.0
            except Exception:
                continue
            factor = max(0.0, factor)
            if side == 2 and kind == 10:
                group = runtime["bullet_type"]
                group[sub_id] = float(group.get(sub_id, 1.0)) * factor
            elif side == 2 and kind == 4:
                group = runtime["type_resist"]
                group[sub_id] = float(group.get(sub_id, 1.0)) * factor
            elif side == 4 and kind == 2:
                group = runtime["killer_crit_bonus"]
                group[0] = float(group.get(0, 1.0)) * factor
        return runtime


@dataclass
class ProcessConfig:
    use_custom_skill_order: bool = False
    custom_skill_order_text: str = ""
    field_buffs: FieldBuffConfig = field(default_factory=FieldBuffConfig)

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "ProcessConfig":
        payload = payload or {}
        return cls(
            use_custom_skill_order=bool(payload.get("use_custom_skill_order", False)),
            custom_skill_order_text=str(payload.get("custom_skill_order_text", "") or ""),
            field_buffs=FieldBuffConfig.from_payload(payload.get("field_buffs", {})),
        )


@dataclass
class AppConfig:
    enemy_slots: Dict[int, EnemySlotConfig]
    ally_slots: Dict[int, AllySlotConfig]
    process: ProcessConfig = field(default_factory=ProcessConfig)
