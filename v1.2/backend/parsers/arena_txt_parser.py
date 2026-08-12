from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


LUNATIC_STAT_FACTOR = 10.5


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except Exception:
        return default


def find_arena_txt(base_dir: Path) -> Optional[Path]:
    candidates = [
        base_dir / "擂台敌人数据07-12.txt",
        base_dir.parent / "擂台敌人数据07-12.txt",
        Path.cwd() / "擂台敌人数据07-12.txt",
    ]
    for path in candidates:
        if path.exists():
            return path
    matches = sorted(base_dir.glob("*07-12.txt"))
    return matches[0] if matches else None


def _scaled(value: Any) -> int:
    return int(round(_to_int(value, 0) * LUNATIC_STAT_FACTOR))


def parse_arena_txt(source: Path) -> Dict[str, Any]:
    text = source.read_text(encoding="utf-8", errors="ignore")
    pattern = re.compile(
        r"\{(?P<arena_id>\d+),(?P<character_id>\d+),\"(?P<name>[^\"]*)\",\{(?P<stats>[^}]*)\},"
        r"(?P<target>\d+),(?P<unknown>\d+),(?:[^,]*,){3}(?P<barrier>\d+),\{(?P<quality>[^}]*)\},(?P<link>\d+)\},?"
    )
    rows: List[Dict[str, Any]] = []
    for match in pattern.finditer(text):
        arena_id = _to_int(match.group("arena_id"), 0)
        if not (200001 <= arena_id <= 300268):
            continue
        prefix = arena_id // 100000
        if prefix not in {2, 3}:
            continue
        stats = [_to_int(part.strip(), 0) for part in match.group("stats").split(",")]
        if len(stats) < 5:
            continue
        quality = [_to_int(part.strip(), 1) for part in match.group("quality").split(",")]
        row = {
            "arena_id": arena_id,
            "sheet_key": "weekly1" if prefix == 2 else "weekly2",
            "character_id": _to_int(match.group("character_id"), 0),
            "name": match.group("name"),
            "yang_atk": _scaled(stats[1]),
            "yang_def": _scaled(stats[2]),
            "yin_atk": _scaled(stats[3]),
            "yin_def": _scaled(stats[4]),
            "speed": _scaled(500),
            "barrier_count": _to_int(match.group("barrier"), 7),
            "quality": [1] * 9,
            "source_quality_raw": quality,
            "skill_effects": [],
        }
        rows.append(row)
    return {
        "parser_version": 1,
        "source": str(source),
        "stat_factor": LUNATIC_STAT_FACTOR,
        "rows": rows,
    }
