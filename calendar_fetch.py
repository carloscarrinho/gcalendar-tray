#!/usr/bin/env python3
"""Entry point invoked by Service.qml: ``python3 calendar_fetch.py [--compact] [url-or-path ...]``.

Prints one JSON object for the bar widget. The logic lives in the
``gcal_tray`` package next to this file (stdlib-only, runs on system python3).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gcal_tray.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
