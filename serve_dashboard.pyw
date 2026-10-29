"""Windowless dashboard launcher (for pythonw / logon tasks). Works from any working directory."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
# pythonw has no console; keep server output in a log file instead.
sys.stdout = sys.stderr = open(os.path.join(ROOT, "logs", "dashboard.log"), "a", encoding="utf-8", buffering=1)

from dashboard.app import main  # noqa: E402

main()
