#!/usr/bin/env python3
"""Runner script for 17-0 Discord Bot with automatic virtual environment resolution."""

import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Check if dependencies are missing in the current Python interpreter
# and automatically forward execution to .venv if present.
venv_python_win = BASE_DIR / ".venv" / "Scripts" / "python.exe"
venv_python_unix = BASE_DIR / ".venv" / "bin" / "python"

try:
    import discord
    import aiosqlite
    import pandas
except ModuleNotFoundError:
    if venv_python_win.exists() and sys.executable.lower() != str(venv_python_win).lower():
        sys.exit(subprocess.call([str(venv_python_win)] + sys.argv))
    elif venv_python_unix.exists() and sys.executable != str(venv_python_unix):
        sys.exit(subprocess.call([str(venv_python_unix)] + sys.argv))
    else:
        print("Error: Missing required packages (discord.py, aiosqlite, pandas).")
        print("Please install dependencies via: pip install -r requirements.txt")
        sys.exit(1)

# Add 17_0_bot directory to sys.path
sys.path.insert(0, str(BASE_DIR / "17_0_bot"))

from bot import main

if __name__ == "__main__":
    main()
