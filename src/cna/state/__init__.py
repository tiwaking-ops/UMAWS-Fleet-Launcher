"""Serialisable CNA game state.

The state is a plain JSON mapping so it can be saved, hashed, replayed and
passed to the decision engine without adapters.  The model module owns the
schema version and the deterministic JSON/hash helpers.
"""

from .model import (SCHEMA_VERSION, StateError, canonical_json,
                    decode_rng_state, encode_rng_state, from_json, new_state,
                    state_hash, to_json, validate_state)

__all__ = [
    "SCHEMA_VERSION", "StateError", "canonical_json", "decode_rng_state",
    "encode_rng_state", "from_json", "new_state", "state_hash", "to_json",
    "validate_state",
]
