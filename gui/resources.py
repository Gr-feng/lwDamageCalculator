from __future__ import annotations

import os
import sys


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", BASE_DIR)
    return os.path.join(base_path, relative_path)


def data_table_path(filename: str) -> str:
    primary = resource_path(os.path.join("data_tables", filename))
    if os.path.exists(primary):
        return primary
    return resource_path(filename)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
APP_DIR = (
    os.path.dirname(os.path.abspath(sys.executable))
    if getattr(sys, "frozen", False)
    else BASE_DIR
)

DATA_DIR = resource_path("datajson")
CHARACTER_CSV_PATH = data_table_path("characters.csv")
PRESET_DIR = os.path.join(APP_DIR, "presets")
NOTICE_JSON_PATH = resource_path(os.path.join("gui", "resources", "startup_notice.json"))
ICON_PATH = resource_path(os.path.join("gui", "resources", "app.ico"))
TRIBE_CSV_PATH = data_table_path("tribe_extracted.csv")
BUFF_XLSX_PATH = resource_path("LW全技能总览.xlsx")
TRANSLATED_CHARACTER_CSV_PATH = data_table_path("touhou_characters_translated.csv")
EQUIPMENT_TXT_PATH = resource_path("绘卷buff03-26.txt")
EQUIPMENT_JSON_PATH = resource_path("equipment_data.json")
RECOMMENDED_EQUIPMENT_CSV_PATH = data_table_path("recommended.csv")
LOCAL_TRANSLATIONS_JSON_PATH = resource_path("local_translations.json")
BUFF_TRANSLATION_CSV_PATH = data_table_path("buff_translation.csv")
BUFF_EFFECT_TEMPLATE_CSV_PATH = data_table_path("buff_effect_templates.csv")

os.makedirs(PRESET_DIR, exist_ok=True)
