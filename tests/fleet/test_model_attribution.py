"""MODEL_SERVED and bundle attribution must always be explicit (H4)."""

from __future__ import annotations

from pathlib import Path

from _fleet_fixtures import FIXTURE_ROOT, fake_profile, make_task
from fleet.harness import Harness
from fleet.profiles import Profile
from fleet.state import FleetState


def _harness(kernel, policy=None):
    state = FleetState.load(Path(kernel.repo.root) / ".pm" / "fleet-state.json")
    pol = policy if policy is not None else kernel.policy()
    return Harness(kernel, state, policy=pol, fixture_root=FIXTURE_ROOT)


def _model_served_events(kernel, task_id):
    return [e for e in kernel.events()
            if e.type == "MODEL_SERVED" and e.subject == task_id]


def test_direct_profile_emits_unavailable_attribution(fake_kernel):
    task = make_task(fake_kernel, oracles=["python -c \"print('ok')\""])
    harness = _harness(fake_kernel)
    profile = Profile.from_dict(fake_profile("fake-a"))
    assert profile.via_gateway is False

    result = harness.run(task, profile)

    assert result.outcome == "submitted", result.to_dict()
    events = _model_served_events(fake_kernel, task.id)
    assert events
    payload = events[-1].payload
    assert payload["served_models"] == ["unavailable"]
    assert payload["source"] == "unavailable"

    assert result.bundle is not None
    resolved = result.bundle["resolved_models"]
    assert resolved and resolved[0]["served_models"] == ["unavailable"]
    assert resolved[0]["source"] == "unavailable"


def test_gateway_profile_preserves_real_served_model(fake_kernel, monkeypatch):
    task = make_task(fake_kernel, oracles=["python -c \"print('ok')\""])
    profile = Profile.from_dict(fake_profile("gw-a"))
    profile.via_gateway = True
    profile.model = "dep/model-a"

    policy = dict(fake_kernel.policy())
    policy["gateway"] = {"base_url": "http://127.0.0.1:9"}

    import fleet.harness as harness_mod

    def fake_served(gateway_url, deployment, *, start, end, timeout=10.0):
        assert gateway_url == "http://127.0.0.1:9"
        assert deployment == "dep/model-a"
        return {"real/model-x"}

    monkeypatch.setattr(harness_mod.provenance_mod, "served_models_for_run", fake_served)

    harness = _harness(fake_kernel, policy=policy)
    result = harness.run(task, profile)

    assert result.outcome == "submitted", result.to_dict()
    events = _model_served_events(fake_kernel, task.id)
    assert events
    payload = events[-1].payload
    assert payload["served_models"] == ["real/model-x"]
    assert payload["source"] == "gateway-window"
    assert payload["deployment"] == "dep/model-a"

    assert result.bundle is not None
    resolved = result.bundle["resolved_models"]
    assert resolved and resolved[0]["served_models"] == ["real/model-x"]
    assert resolved[0]["source"] == "gateway-window"
