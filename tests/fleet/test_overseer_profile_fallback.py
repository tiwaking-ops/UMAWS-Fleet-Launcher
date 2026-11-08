"""The Overseer must not be blocked by a disabled profile at the head of the list.

On 2026-11-07 all nine OVERSEER_WOKEN events failed with "the Overseer profile
pi-orca-deepseek is disabled" — that profile is first in `agents.toml` — so no
Overseer session ran and no stale hint could be corrected.
"""

from types import SimpleNamespace

from fleet.overseer import OverseerRunner


class _Kernel:
    def __init__(self):
        self.events = []

    def record_event(self, event_type, **kwargs):
        self.events.append((event_type, kwargs))


class _State:
    def __init__(self, enabled):
        self.enabled = enabled

    def cooling(self):
        return False


class _FleetState:
    def __init__(self, states):
        self.states = states

    def profile(self, profile_id):
        return self.states[profile_id]


def _runner(states, started_ids):
    runner = OverseerRunner(kernel=_Kernel(), fleet_state=_FleetState(states))
    runner.ordered_profiles = lambda: [SimpleNamespace(id=pid) for pid in states]

    def fake_start(profile, project):
        started_ids.append(profile.id)
        return f"session:{profile.id}"

    runner._start = fake_start
    return runner


def test_disabled_head_profile_is_skipped():
    started = []
    runner = _runner({"pi-orca-deepseek": _State(False),
                      "kilo-auto": _State(True)}, started)
    wake = runner.wake("periodic")
    assert wake.started is True
    assert wake.profile == "kilo-auto"
    assert started == ["kilo-auto"]


def test_all_disabled_reports_every_profile():
    started = []
    runner = _runner({"pi-orca-deepseek": _State(False),
                      "kilo-auto": _State(False)}, started)
    wake = runner.wake("periodic")
    assert wake.started is False
    assert "pi-orca-deepseek" in (wake.error or "")
    assert "kilo-auto" in (wake.error or "")
    assert started == []
