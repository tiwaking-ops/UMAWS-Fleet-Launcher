"""Build the P1b-P4 case backlog from the coverage ledger."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "coverage" / "rules_coverage.json"
OUT = ROOT / "docs" / "plans" / "cna-p1b-p4-case-backlog.csv"

# section -> (phase, work package, priority, target module, data gates)
SECTIONS = {
    "1": ("Reference", "REF", "P3", "reference", ""),
    "2": ("Reference", "REF", "P3", "reference", ""),
    "3": ("Reference", "REF", "P3", "reference.glossary", ""),
    "4": ("Reference", "REF", "P3", "reference.data", "R-04, R-06"),
    "65": ("Reference", "REF", "P3", "reference", ""),
    "5": ("P1b", "P1b.1", "P0", "land.sequence", ""),
    "6": ("P1b", "P1b.1", "P0", "land.capability", "R-04"),
    "7": ("P1b", "P1b.1", "P0", "land.initiative", "R-04, R-05"),
    "8": ("P1b", "P1b.1", "P0", "land.movement", "R-04, R-05"),
    "9": ("P1b", "P1b.1", "P0", "land.stacking", "R-04"),
    "10": ("P1b", "P1b.1", "P0", "land.zoc", "R-05"),
    "29": ("P1b", "P1b.1", "P0", "land.weather", "R-04, R-05"),
    "11": ("P1b", "P1b.2", "P0", "land.combat", "R-04"),
    "12": ("P1b", "P1b.2", "P0", "land.combat.barrage", "R-04"),
    "13": ("P1b", "P1b.2", "P0", "land.combat.retreat", "R-04"),
    "14": ("P1b", "P1b.2", "P0", "land.combat.antiarmor", "R-04"),
    "15": ("P1b", "P1b.2", "P0", "land.combat.close_assault", "R-04"),
    "16": ("P1b", "P1b.3", "P1", "land.patrols", "R-04, R-05"),
    "17": ("P1b", "P1b.3", "P1", "land.morale", "R-04"),
    "18": ("P1b", "P1b.3", "P1", "land.reserve", ""),
    "32": ("P1b", "P1b.4", "P0", "land.abstract_supply_air", "R-04, R-06"),
    "19": ("P1b", "P1b.5", "P1", "land.organization", "R-04, R-06, R-07"),
    "20": ("P1b", "P1b.5", "P1", "land.reinforcements", "R-03, R-04, R-06"),
    "21": ("P1b", "P1b.6", "P2", "land.breakdown", "R-04, R-06"),
    "22": ("P1b", "P1b.6", "P2", "land.repair", "R-04, R-06"),
    "23": ("P1b", "P1b.6", "P2", "land.engineers", ""),
    "24": ("P1b", "P1b.6", "P2", "land.construction", "R-04, R-05"),
    "25": ("P1b", "P1b.6", "P2", "land.fortifications", "R-04"),
    "26": ("P1b", "P1b.6", "P2", "land.minefields", "R-04"),
    "27": ("P1b", "P1b.7", "P2", "land.raiders", "R-04, R-05"),
    "28": ("P1b", "P1b.7", "P2", "land.pow", "R-04"),
    "30": ("P1b", "P1b.7", "P2", "land.med_fleet", "R-04, R-05"),
    "31": ("P1b", "P1b.7", "P2", "land.rommel", "R-04"),
    "59": ("P1c", "P1c.1", "P1", "scenario.loader", "R-04, R-05, R-06"),
    "60": ("P1c", "P1c.2", "P1", "scenario.data", "R-03, R-04, R-05, R-06, R-07"),
    "48": ("P2", "P2.1", "P0", "logistics.sequence", "R-09"),
    "49": ("P2", "P2.1", "P0", "logistics.fuel", "R-04, R-09"),
    "50": ("P2", "P2.1", "P0", "logistics.ammunition", "R-04, R-09"),
    "51": ("P2", "P2.1", "P0", "logistics.stores", "R-04, R-09"),
    "52": ("P2", "P2.1", "P0", "logistics.water", "R-04, R-09"),
    "53": ("P2", "P2.2", "P1", "logistics.trucks", "R-04, R-09"),
    "54": ("P2", "P2.2", "P1", "logistics.supply_coordination", "R-05, R-09"),
    "55": ("P2", "P2.2", "P1", "logistics.ports", "R-05, R-09"),
    "56": ("P2", "P2.2", "P1", "logistics.axis_naval", "R-04, R-09"),
    "57": ("P2", "P2.2", "P1", "logistics.commonwealth_base", "R-05, R-09"),
    "58": ("P2", "P2.3", "P2", "logistics.abstract_air", "R-09"),
    "33": ("P3", "P3.1", "P0", "air.sequence", "R-08"),
    "34": ("P3", "P3.1", "P0", "air.aircraft", "R-04, R-08"),
    "35": ("P3", "P3.1", "P0", "air.ground_support", "R-04, R-08"),
    "36": ("P3", "P3.1", "P0", "air.facilities", "R-05, R-08"),
    "37": ("P3", "P3.2", "P1", "air.flight", "R-04, R-08"),
    "38": ("P3", "P3.2", "P1", "air.maintenance", "R-04, R-08"),
    "39": ("P3", "P3.2", "P1", "air.missions", "R-04, R-08"),
    "40": ("P3", "P3.3", "P1", "air.fighter_combat", "R-04, R-08"),
    "41": ("P3", "P3.3", "P1", "air.bombing", "R-04, R-08"),
    "42": ("P3", "P3.3", "P1", "air.noncombat_missions", "R-04, R-08"),
    "43": ("P3", "P3.3", "P1", "air.axis_bases", "R-05, R-08"),
    "44": ("P3", "P3.3", "P1", "air.malta", "R-04, R-05, R-08"),
    "45": ("P3", "P3.3", "P1", "air.air_to_air", "R-04, R-08"),
    "46": ("P3", "P3.3", "P1", "air.antiaircraft", "R-04, R-08"),
    "47": ("P3", "P3.4", "P2", "air.abstract_logistics", "R-08"),
    "61": ("P4", "P4.1", "P1", "scenario.data", "R-03, R-04, R-05, R-06"),
    "62": ("P4", "P4.1", "P1", "scenario.data", "R-03, R-04, R-05, R-06"),
    "63": ("P4", "P4.1", "P1", "scenario.data", "R-03, R-04, R-05, R-06"),
    "64": ("P4", "P4.2", "P0", "scenario.campaign", "R-03, R-04, R-05, R-06, R-07"),
}

PHASE_ORDER = {"P1b": 0, "P1c": 1, "P2": 2, "P3": 3, "P4": 4,
               "Reference": 5}


def main() -> int:
    data = json.loads(COVERAGE.read_text(encoding="utf-8"))
    sections = {}
    for case in data["cases"]:
        if case["case"].endswith(".0"):
            sections[case["case"].split(".")[0]] = case["title"]

    rows = []
    for case in data["cases"]:
        if case["status"] == "implemented":
            continue
        section = case["case"].split(".")[0]
        phase, work_package, priority, target, gaps = SECTIONS[section]
        if phase == "Reference":
            disposition = "reference"
        elif case["status"] == "deferred":
            disposition = "phase_gate"
        else:
            disposition = "implement"
        rows.append({
            "phase": phase,
            "work_package": work_package,
            "priority": priority,
            "section": int(section),
            "section_title": sections.get(section, ""),
            "case": case["case"],
            "title": case["title"],
            "status": case["status"],
            "disposition": disposition,
            "target_module": target,
            "data_gaps": gaps,
            "rules_file": case["rules_file"],
            "line": case["line"],
            "source": case.get("source", ""),
            "tests": ";".join(case.get("tests", [])),
            "coverage_reason": case.get("reason", ""),
        })

    rows.sort(key=lambda row: (
        PHASE_ORDER[row["phase"]], row["work_package"], row["section"],
        tuple(int(part) for part in row["case"].split(".") if part.isdigit())
    ))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print("rows", len(rows))
    print("by_disposition", dict(Counter(row["disposition"] for row in rows)))
    print("by_phase", dict(Counter(row["phase"] for row in rows)))
    print("by_priority", dict(Counter(row["priority"] for row in rows)))
    print("out", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
