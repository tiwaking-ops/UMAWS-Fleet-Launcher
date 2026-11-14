"""Data-loading primitives for the CNA digital edition."""

from .r04 import (BreakdownTable, load_breakdown_table, load_off_map_chart,
                  load_tec)
from .r05 import load_rail_map
from .scenario import Scenario, ScenarioHex, load_scenario
from .schema import (
    PROVENANCE_PREFIXES,
    STATUSES,
    DataError,
    DataHeader,
    require_playable,
    validate_header,
    validate_provenance,
    validate_record,
    validate_status,
    validate_table,
)

__all__ = [
    "BreakdownTable",
    "Scenario",
    "ScenarioHex",
    "load_breakdown_table",
    "load_off_map_chart",
    "load_rail_map",
    "load_scenario",
    "load_tec",
    "PROVENANCE_PREFIXES",
    "STATUSES",
    "DataError",
    "DataHeader",
    "require_playable",
    "validate_header",
    "validate_provenance",
    "validate_record",
    "validate_status",
    "validate_table",
]
