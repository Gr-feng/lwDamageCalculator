# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


SPEC_DIR = Path.cwd()


a = Analysis(
    ["desktop_app.py"],
    pathex=[str(SPEC_DIR)],
    binaries=[],
    datas=[
        ("web", "web"),
        ("assets", "assets"),
        ("datajson", "datajson"),
        ("presets", "presets"),
        ("gui/resources", "gui/resources"),
        ("characters.csv", "."),
        ("touhou_characters_translated.csv", "."),
        ("tribe_extracted.csv", "."),
        ("buff_translation.csv", "."),
        ("local_translations.json", "."),
        ("equipment_data.json", "."),
        ("recommended.csv", "."),
        ("attack5_candidates.csv", "."),
        ("LW全技能总览.xlsx", "."),
        ("绘卷buff03-26.txt", "."),
        ("绘卷buff04-04国服.txt", "."),
        ("D绘卷.txt", "."),
        ("../复灵敌人数据06-19.lua", "."),
    ],
    hiddenimports=[
        "webview",
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide6",
        "shiboken6",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "qtpy",
        "gevent",
        "tkinter",
        "_tkinter",
        "numpy",
        "openpyxl",
        "pandas",
        "PIL",
        "pygame",
        "scipy",
        "lxml",
        "matplotlib",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="lw_damage_calculator_v1_2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["app.ico"],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="lw_damage_calculator_v1_2",
)
