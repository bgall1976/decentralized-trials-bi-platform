"""Central config for the local pipeline. Cloud config comes from the .bicepparam file."""
from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))

LANDING = DATA_DIR / "landing"
BRONZE = DATA_DIR / "bronze"
SILVER = DATA_DIR / "silver"
GOLD = DATA_DIR / "gold"

SEED = int(os.environ.get("SEED", "42"))

# Funnel stages in order. Mission framing: every stage is a place time can be lost (Faster)
# and a conversion point whose stability we track (Predictable).
FUNNEL_STAGES = [
    "lead",
    "pre_screened",
    "consented",
    "screened",
    "randomized",
    "enrolled",
    "completed",
]

for _d in (LANDING, BRONZE, SILVER, GOLD):
    _d.mkdir(parents=True, exist_ok=True)
