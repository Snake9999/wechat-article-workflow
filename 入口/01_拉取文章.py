#!/usr/bin/env python3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
cmd = ['python3', str(ROOT / '脚本' / 'pull_from_wewe.py')]
raise SystemExit(subprocess.run(cmd, cwd=ROOT).returncode)
