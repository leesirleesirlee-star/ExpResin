"""Canonical breakthrough regression: time, reported concentration, derived BV."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ["EXPRESIN_DATA_DIR"] = str(ROOT / ".deepworks" / "tmp" / "canonical-breakthrough-test")
sys.path.insert(0, str(ROOT / "expresin-pipeline" / "src"))
sys.path.insert(0, str(ROOT / "expresin-pipeline" / "server"))

import app as backend  # noqa: E402
from canonical import build_canonical  # noqa: E402

EXAMPLE = ROOT / "materials" / "record-templates" / "Column_Record_Template_v1_example_filled.xlsx"
checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


recognized = backend.analyze_workbook(EXAMPLE)
canonical = build_canonical(
    EXAMPLE,
    recognized,
    "RES-20261110-901",
    {"initial_concentration": 120, "bed_volume": 10, "flow_rate": 2},
)
rows = [row for row in canonical.get("rows") or [] if row.get("kind") == "sample_measurement"]

check(len(recognized.get("regions") or []) == 1, "expected one recognized region")
check(len(rows) == 10, f"expected 10 sample rows, got {len(rows)}")
check("time_min" in (canonical.get("columns") or []), "time_min must be in canonical columns")
check(rows[0]["time_min"] == 0, "first time_min")
check(rows[-1]["time_min"] == 300, "last time_min")
check(rows[0]["bed_volume"] == 0, "first derived BV")
check(abs(rows[-1]["bed_volume"] - 60) < 1e-9, "last derived BV")
check(rows[0]["volume_ml"] == 0, "first derived volume")
check(abs(rows[-1]["volume_ml"] - 600) < 1e-9, "last derived volume")
check(rows[0]["conc_ppm_reported"] == 0.5, "first reported concentration")
check(rows[-1]["conc_ppm_reported"] == 116, "last reported concentration")
check(rows[0]["conc_ppm_computed"] is None, "no signal area must not invent computed concentration")
check(rows[0]["method"] == "reported_concentration", "reported-only method")
check(any("时间 × 流速" in note for note in canonical.get("notes") or []), "derived-axis note")

print(f"CANONICAL_BREAKTHROUGH_OK checks={checks}")
