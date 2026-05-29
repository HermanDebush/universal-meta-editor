"""
Universal Meta Editor
---------------------
Edit metadata of .docx, .xlsx, .pptx and other Office Open XML files,
Windows PE executables (.exe, .dll) and HTML pages — no extra software needed.

Usage:
    python main.py
    python main.py path/to/file.docx   # open file directly
"""

import sys
from pathlib import Path


def main():
    from gui.app import App

    app = App()

    # Optional: open a file passed as CLI argument
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if path.is_file():
            app.after(100, lambda: app._load_file(path))

    app.mainloop()


if __name__ == "__main__":
    main()
