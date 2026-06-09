#!/usr/bin/env python3
"""LAAP Zero-Dependency Entry Point.

This file has NO external imports at module level.
Everything is imported inside try/except so the user
always sees what went wrong.
"""
import os
import sys
import traceback

_LAAP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(_LAAP_DIR)
sys.path.insert(0, _LAAP_DIR)

# Write log early
_LOG_DIR = os.path.join(os.path.expanduser("~"), ".laap", "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_FILE = os.path.join(_LOG_DIR, "launcher.log")

def _log(msg):
    with open(_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{msg}\n")

_log("=== LAAP START ===")
_log(f"Python: {sys.version}")
_log(f"CWD: {os.getcwd()}")
_log(f"PATH[0]: {sys.path[0]}")

try:
    from laap.api.cli import main
    _log("Import OK")
    main()
    _log("=== LAAP EXIT NORMAL ===")
except SystemExit:
    _log("=== LAAP EXIT (sys.exit) ===")
except Exception as e:
    _log(f"=== LAAP CRASH: {e} ===")
    tb = traceback.format_exc()
    _log(tb)
    print(f"\n[LAAP] FATAL ERROR: {e}")
    print(f"[LAAP] See log: {_LOG_FILE}")
    print(f"[LAAP] Full traceback:")
    traceback.print_exc()
    print(f"\n[LAAP] Press Enter to exit...")
    try:
        input()
    except:
        pass
    sys.exit(1)
