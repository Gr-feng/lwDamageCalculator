# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


SPEC_DIR = Path.cwd()


def _entry_strings(entry):
    values = []
    for value in entry[:3]:
        if isinstance(value, str):
            values.append(value.replace("\\", "/").lower())
    return values


def _matches_any(entry, patterns):
    texts = _entry_strings(entry)
    return any(pattern in text for text in texts for pattern in patterns)


def _filter_toc(toc, blocked_patterns):
    filtered = [entry for entry in toc if not _matches_any(entry, blocked_patterns)]
    return toc.__class__(filtered)


QT_BLOCKLIST = (
    "/pyside6/qml/",
    "/pyside6/translations/",
    "/pyside6/qt6quick",
    "/pyside6/qt6qml",
    "/pyside6/qt6pdf",
    "/pyside6/qt6designer",
    "/pyside6/qt63d",
    "/pyside6/qt6charts",
    "/pyside6/qt6graphs",
    "/pyside6/qt6location",
    "/pyside6/qt6multimedia",
    "/pyside6/qt6positioning",
    "/pyside6/qt6quickcontrols2",
    "/pyside6/qt6quickdialogs2",
    "/pyside6/qt6quicktemplates2",
    "/pyside6/qt6remoteobjects",
    "/pyside6/qt6scxml",
    "/pyside6/qt6sensors",
    "/pyside6/qt6serial",
    "/pyside6/qt6sql",
    "/pyside6/qt6statemachine",
    "/pyside6/qt6test",
    "/pyside6/qt6texttospeech",
    "/pyside6/qt6virtualkeyboard",
    "/pyside6/qt6webchannel",
    "/pyside6/qt6webengine",
    "/pyside6/avcodec",
    "/pyside6/avformat",
    "/pyside6/avutil",
    "/pyside6/swresample",
    "/pyside6/swscale",
    "/pyside6/plugins/assetimporters/",
    "/pyside6/plugins/designer/",
    "/pyside6/plugins/generic/",
    "/pyside6/plugins/geoservices/",
    "/pyside6/plugins/iconengines/qsvgicon",
    "/pyside6/plugins/imageformats/qpdf",
    "/pyside6/plugins/imageformats/qsvg",
    "/pyside6/plugins/multimedia/",
    "/pyside6/plugins/networkinformation/",
    "/pyside6/plugins/platformthemes/",
    "/pyside6/plugins/qmltooling/",
    "/pyside6/plugins/sceneparsers/",
    "/pyside6/plugins/sqldrivers/",
    "/pyside6/plugins/texttospeech/",
    "/pyside6/plugins/tls/",
    "/pyside6/plugins/platforms/qoffscreen",
    "/pyside6/plugins/platforms/qminimal",
    "/pyside6/plugins/platforms/qdirect2d",
    "/pyside6/plugins/platforms/qwebgl",
)


a = Analysis(
    ["gui_app.py"],
    pathex=[str(SPEC_DIR)],
    binaries=[],
    datas=[
        ("characters.csv", "."),
        ("datajson", "datajson"),
        ("gui/resources", "gui/resources"),
        ("tribe_extracted.csv", "."),
        ("equipment_data.json", "."),
        ("recommended.csv", "."),
        ("local_translations.json", "."),
        ("buff_translation.csv", "."),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["pyi_rth_qt_env.py"],
    excludes=[
        "PySide6.Qt3DAnimation",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DExtras",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DRender",
        "PySide6.QtBluetooth",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtDesigner",
        "PySide6.QtGraphs",
        "PySide6.QtGraphsWidgets",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtOpenGLWidgets",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtPositioning",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.QtQuickControls2",
        "PySide6.QtQuickDialogs2",
        "PySide6.QtQuickWidgets",
        "PySide6.QtRemoteObjects",
        "PySide6.QtScxml",
        "PySide6.QtSensors",
        "PySide6.QtSerialBus",
        "PySide6.QtSerialPort",
        "PySide6.QtSql",
        "PySide6.QtStateMachine",
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
        "PySide6.QtTest",
        "PySide6.QtTextToSpeech",
        "PySide6.QtWebChannel",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets",
        "matplotlib",
        "numpy",
        "openpyxl",
        "pandas",
        "PIL",
        "pygame",
        "scipy",
        "lxml",
    ],
    noarchive=False,
    optimize=0,
)

a.binaries = _filter_toc(a.binaries, QT_BLOCKLIST)
a.datas = _filter_toc(a.datas, QT_BLOCKLIST)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="lw_damage_calculator",
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
    icon=["gui/resources/app.ico"],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="lw_damage_calculator",
)
