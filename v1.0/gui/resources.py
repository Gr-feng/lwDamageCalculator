from __future__ import annotations

import os
import sys


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
APP_DIR = (
    os.path.dirname(os.path.abspath(sys.executable))
    if getattr(sys, "frozen", False)
    else BASE_DIR
)

DATA_DIR = resource_path("datajson")
CHARACTER_CSV_PATH = resource_path("characters.csv")
PRESET_DIR = os.path.join(APP_DIR, "presets")
NOTICE_JSON_PATH = resource_path(os.path.join("gui", "resources", "startup_notice.json"))
ICON_PATH = resource_path(os.path.join("gui", "resources", "app.ico"))
TRIBE_CSV_PATH = os.path.join(BASE_DIR, "tribe_extracted.csv")
BUFF_XLSX_PATH = os.path.join(BASE_DIR, "LW全技能总览.xlsx")
TRANSLATED_CHARACTER_CSV_PATH = os.path.join(ROOT_DIR, "touhou_characters_translated.csv")
EQUIPMENT_TXT_PATH = os.path.join(BASE_DIR, "绘卷buff03-26.txt")
EQUIPMENT_JSON_PATH = os.path.join(BASE_DIR, "equipment_data.json")
RECOMMENDED_EQUIPMENT_CSV_PATH = os.path.join(BASE_DIR, "recommended.csv")
LOCAL_TRANSLATIONS_JSON_PATH = os.path.join(BASE_DIR, "local_translations.json")
BUFF_TRANSLATION_CSV_PATH = os.path.join(BASE_DIR, "buff_translation.csv")

os.makedirs(PRESET_DIR, exist_ok=True)
