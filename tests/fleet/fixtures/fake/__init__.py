"""The fake CLI's own fixtures.

These are **synthetic**: they describe exactly what ``tests/fleet/fakecli.py``
prints, and they make no claim about any real provider.  A real adapter
never reuses them (fleet amendment section 12.E).
"""

# tests/fleet/fixtures/fake/quota.txt
SYNTHETIC_QUOTA = r"SYNTHETIC-FAILURE-QUOTA"
SYNTHETIC_AUTH = r"SYNTHETIC-FAILURE-AUTH"
SYNTHETIC_NETWORK = r"SYNTHETIC-FAILURE-NETWORK"
SYNTHETIC_MODEL_GONE = r"SYNTHETIC-FAILURE-MODEL-GONE"
