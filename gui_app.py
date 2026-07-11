import os
import sys


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    v1_dir = os.path.join(base_dir, "v1.0")
    if v1_dir not in sys.path:
        sys.path.insert(0, v1_dir)
    from gui.main import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
