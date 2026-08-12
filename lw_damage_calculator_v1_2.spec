# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


SPEC_DIR = Path.cwd()


def existing_datas():
    required = [
        ("web", "web"),
        ("assets", "assets"),
        ("datajson", "datajson"),
        ("data_tables", "data_tables"),
        ("presets", "presets"),
        ("gui/resources", "gui/resources"),
        ("local_translations.json", "."),
        ("equipment_data.json", "."),
    ]
    optional = [
        ("LW全技能总览.xlsx", "."),
        ("../LW全技能总览.xlsx", "."),
        ("擂台敌人数据详情.xlsx", "."),
        ("../擂台敌人数据详情.xlsx", "."),
        ("绘卷buff03-26.txt", "."),
        ("../绘卷buff03-26.txt", "."),
        ("../v1.0/绘卷buff03-26.txt", "."),
        ("绘卷buff04-04国服.txt", "."),
        ("../v1.0/绘卷buff04-04国服.txt", "."),
        ("D绘卷.txt", "."),
        ("../v1.0/D绘卷.txt", "."),
        ("复灵敌人数据06-19.lua", "."),
        ("../复灵敌人数据06-19.lua", "."),
        ("擂台敌人数据07-12.txt", "."),
    ]
    out = list(required)
    seen = {(Path(source).name, target) for source, target in required}
    for source, target in optional:
        path = SPEC_DIR / source
        key = (Path(source).name, target)
        if path.exists() and key not in seen:
            out.append((source, target))
            seen.add(key)
    return out


a = Analysis(
    ["desktop_app.py"],
    pathex=[str(SPEC_DIR)],
    binaries=[],
    datas=existing_datas(),
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
