"""
Production Entry Point for aura.exe (Management CLI).
"""

from __future__ import annotations

import sys
from aura.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
