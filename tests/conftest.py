from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = (
    REPOSITORY_ROOT
    / "skills"
    / "bugbash-autopilot"
    / "scripts"
)
sys.path.insert(0, str(SKILL_SCRIPTS))
