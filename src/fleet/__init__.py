"""The UMAWS Fleet — dispatcher, adapters, recovery ladder (amendment A1).

Standard library only (fleet amendment section 7.1).

The Fleet is the half of the system that actually runs agents.  The Kernel
(:mod:`pmk`) owns the state; the Fleet owns the processes.

    Dispatcher  -> selects a profile, claims a task, writes the order,
                   spawns the CLI, supervises it, classifies the outcome,
                   and hands the result back to the Kernel.
"""

from __future__ import annotations

__all__ = [
    "adapters", "classify", "dispatcher", "harness", "order", "profiles",
    "recover", "select", "spawn", "state",
]
