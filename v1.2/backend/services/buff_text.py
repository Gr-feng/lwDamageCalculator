from __future__ import annotations

import csv
import os
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional


TemplateRow = Dict[str, str]


def _norm(value: Any) -> str:
    return str(value if value is not None else "").strip()


@lru_cache(maxsize=8)
def load_buff_templates(csv_path: str) -> List[TemplateRow]:
    if not csv_path or not os.path.exists(csv_path):
        return []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        return [dict(row) for row in csv.DictReader(f) if row and row.get("id")]


def _score_template(row: TemplateRow, query: Dict[str, str]) -> Optional[int]:
    score = 0
    for key in ("id", "sub_id", "target", "value", "duration"):
        expected = _norm(row.get(key))
        if not expected:
            continue
        if expected != _norm(query.get(key)):
            return None
        score += 1
    return score


def find_buff_template(templates: Iterable[TemplateRow], *, buff_id: Any, sub_id: Any, target: Any, value: Any, duration: Any) -> Optional[TemplateRow]:
    query = {
        "id": _norm(buff_id),
        "sub_id": _norm(sub_id),
        "target": _norm(target),
        "value": _norm(value),
        "duration": _norm(duration),
    }
    best: Optional[TemplateRow] = None
    best_score = -1
    for row in templates:
        score = _score_template(row, query)
        if score is None:
            continue
        if score > best_score:
            best = row
            best_score = score
    return best


def render_buff_template(template: TemplateRow, values: Dict[str, Any]) -> str:
    text = str(template.get("description") or "")
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text
