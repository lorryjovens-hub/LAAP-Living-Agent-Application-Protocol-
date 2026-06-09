#!/usr/bin/env python3
"""LAAP Universal Launcher - Zero crash guarantee"""
import sys, os, traceback, logging

_LAAP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(_LAAP_DIR)
sys.path.insert(0, _LAAP_DIR)

# Set up error logging to file
_log_dir = os.path.join(os.path.expanduser("~"), ".laap", "logs")
os.makedirs(_log_dir, exist_ok=True)
_log_file = os.path.join(_log_dir, "launcher.log")
logging.basicConfig(
    filename=_log_file, level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def _log(msg):
    print(f"[LAAP] {msg}")
    logging.info(msg)

def _error(msg):
    print(f"[LAAP] ERROR: {msg}")
    logging.error(msg)

try:
    # Step 1: Check Python version
    if sys.version_info < (3, 10):
        _error(f"Python 3.10+ required, got {sys.version}")
        sys.exit(1)
    _log(f"Python {sys.version}")

    # Step 2: Auto-install dependencies
    _missing = []
    for mod in ["numpy", "httpx"]:
        try:
            __import__(mod)
        except ImportError:
            _missing.append(mod)
    
    if _missing:
        _log(f"Installing missing deps: {_missing}")
        import subprocess
        r = subprocess.run([sys.executable, "-m", "pip", "install"] + _missing + ["-q"],
                          capture_output=True, text=True)
        if r.returncode != 0:
            _error(f"pip install failed: {r.stderr[:200]}")
            # Try without -q
            r = subprocess.run([sys.executable, "-m", "pip", "install"] + _missing,
                              capture_output=True, text=True)
            if r.returncode != 0:
                _error(f"pip retry failed: {r.stderr[:200]}")

    # Step 3: Import and run
    from laap.api.cli import main
    _log("Launching LAAP...")

    # If stdin/stdout is not a real TTY (IDE / captured / redirected), the
    # full-screen Textual TUI cannot render and will appear to "flash exit".
    # Inject --interactive so we land in the text-based REPL instead.
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        if "--interactive" not in sys.argv and "-i" not in sys.argv \
                and "--task" not in sys.argv and "-t" not in sys.argv:
            print("[LAAP] Non-TTY detected — defaulting to --interactive (REPL) mode.")
            print("[LAAP] For the full-screen TUI, run in a real terminal (Windows Terminal, iTerm2, etc.).\n")
            sys.argv.append("--interactive")

    main()

except Exception as e:
    _error(f"CRASH: {e}")
    traceback.print_exc()
    # Write full traceback to log file
    with open(_log_file, "a") as lf:
        traceback.print_exc(file=lf)
    print(f"\n[LAAP] Fatal error: {e}")
    print(f"[LAAP] See log: {_log_file}")
    print(f"[LAAP] Press Enter to exit...")
    try:
        input()
    except:
        pass
    sys.exit(1)
