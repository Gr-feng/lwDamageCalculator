import os
import sys


def _prepend_path(parts):
    existing = os.environ.get("PATH", "")
    merged = [p for p in parts if p and os.path.isdir(p)]
    if existing:
        merged.append(existing)
    os.environ["PATH"] = os.pathsep.join(merged)


def _add_dll_dirs(parts):
    if not hasattr(os, "add_dll_directory"):
        return
    for path in parts:
        if not path or not os.path.isdir(path):
            continue
        try:
            os.add_dll_directory(path)
        except OSError:
            pass


base = getattr(sys, "_MEIPASS", "")
if base:
    pyside_dir = os.path.join(base, "PySide6")
    shiboken_dir = os.path.join(base, "shiboken6")
    pywin32_dir = os.path.join(base, "pywin32_system32")
    dll_dirs = [base, pyside_dir, shiboken_dir, pywin32_dir]

    _prepend_path(dll_dirs)
    _add_dll_dirs(dll_dirs)

    plugin_dir = os.path.join(pyside_dir, "plugins")
    platform_dir = os.path.join(plugin_dir, "platforms")

    # Avoid inheriting polluted Qt env from conda/system Qt installs.
    os.environ.pop("QML2_IMPORT_PATH", None)
    os.environ["QT_PLUGIN_PATH"] = plugin_dir
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = platform_dir
