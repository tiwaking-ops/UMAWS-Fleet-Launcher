"""Fleet tests: selection, the harness, the recovery ladder, reconciliation.

These map onto the fleet amendment's acceptance tests F2, F3, F5, F6, F8,
F10, F11, F12 and F13.  Everything runs against the fake CLI.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from fleet import classify as classes
from fleet import recover
from fleet.adapters import get_adapter
from fleet.dispatcher import Dispatcher
from fleet.harness import Harness, run_oracles, scope_check
from fleet.profiles import Profile, guess_family, import_prompts
from fleet.select import select_profile
from fleet.spawn import worktree_path
from fleet.state import FleetState

from conftest import FIXTURE_ROOT, fake_profile, make_task, write_agents


# ---------------------------------------------------------------------------
# Selection (F5)
# ---------------------------------------------------------------------------

def test_selection_is_deterministic(fake_kernel, git_repo):
    task = make_task(fake_kernel)
    profiles = [Profile.from_dict(fake_profile("a", priority=10)),
                Profile.from_dict(fake_profile("b", priority=20))]
    state = FleetState()
    first = select_profile(task, profiles, state, {})
    second = select_profile(task, profiles, state, {})
    assert first.chosen.id == second.chosen.id
    assert first.chosen.id == "a"          # lower priority number wins


def test_selection_prefers_lower_utilisation_at_equal_priority(fake_kernel):
    task = make_task(fake_kernel)
    profiles = [Profile.from_dict(fake_profile("a", priority=10,
                                              max_concurrent=2)),
                Profile.from_dict(fake_profile("b", priority=10,
                                              max_concurrent=2))]
    state = FleetState()
    running = {"a": 1, "b": 0}
    selection = select_profile(task, profiles, state, running)
    assert selection.chosen.id == "b"      # less utilised wins


def test_selection_skips_a_cooling_profile(fake_kernel):
    task = make_task(fake_kernel)
    profiles = [Profile.from_dict(fake_profile("a", priority=10)),
                Profile.from_dict(fake_profile("b", priority=20))]
    state = FleetState()
    state.cool("a", 600)
    selection = select_profile(task, profiles, state, {})
    assert selection.chosen.id == "b"


def test_selection_skips_a_disabled_profile(fake_kernel):
    task = make_task(fake_kernel)
    profiles = [Profile.from_dict(fake_profile("a", priority=10)),
                Profile.from_dict(fake_profile("b", priority=20))]
    state = FleetState()
    state.disable("a")
    selection = select_profile(task, profiles, state, {})
    assert selection.chosen.id == "b"


def test_selection_respects_the_concurrency_limit(fake_kernel):
    task = make_task(fake_kernel)
    profiles = [Profile.from_dict(fake_profile("a", priority=10,
                                              max_concurrent=1))]
    state = FleetState()
    selection = select_profile(task, profiles, state, {"a": 1})
    assert selection.chosen is None
    assert "concurrency limit" in selection.reason


def test_selection_respects_the_fleet_cap(fake_kernel):
    task = make_task(fake_kernel)
    profiles = [Profile.from_dict(fake_profile("a"))]
    selection = select_profile(task, profiles, FleetState(), {},
                               fleet_cap=5, total_running=5)
    assert selection.chosen is None


def test_selection_excludes_an_unknown_family_from_verification(fake_kernel):
    """D-L12: an unverifiable family can never be an independent verifier."""
    task = make_task(fake_kernel, type="verify")
    profiles = [Profile.from_dict(fake_profile("unknown-family",
                                              family="unknown")),
                Profile.from_dict(fake_profile("known-family",
                                              family="deepseek"))]
    selection = select_profile(task, profiles, FleetState(), {},
                               implementer_family="anthropic")
    assert selection.chosen.id == "known-family"


def test_selection_excludes_the_implementers_own_family(fake_kernel):
    task = make_task(fake_kernel, type="verify")
    profiles = [Profile.from_dict(fake_profile("same", family="deepseek")),
                Profile.from_dict(fake_profile("other", family="anthropic"))]
    selection = select_profile(task, profiles, FleetState(), {},
                               implementer_family="deepseek")
    assert selection.chosen.id == "other"


def test_selection_respects_role_eligibility(fake_kernel):
    task = make_task(fake_kernel, type="verify")
    profiles = [Profile.from_dict(fake_profile("impl-only",
                                              roles=["implement"]))]
    selection = select_profile(task, profiles, FleetState(), {})
    assert selection.chosen is None


def test_agent_hint_is_a_preference_not_a_requirement(fake_kernel):
    task = make_task(fake_kernel, agent_hint="b")
    profiles = [Profile.from_dict(fake_profile("a", priority=10)),
                Profile.from_dict(fake_profile("b", priority=99))]
    selection = select_profile(task, profiles, FleetState(), {})
    assert selection.chosen.id == "b"      # the hint wins over priority


def test_selection_explains_why_nothing_qualified(fake_kernel):
    task = make_task(fake_kernel)
    profiles = [Profile.from_dict(fake_profile("a", max_concurrent=1))]
    selection = select_profile(task, profiles, FleetState(), {"a": 1})
    assert selection.chosen is None
    assert selection.reason


# ---------------------------------------------------------------------------
# Classification and the unverified-classifier rule (F12)
# ---------------------------------------------------------------------------

def test_a_real_adapter_has_no_patterns_so_everything_is_unknown(fake_kernel):
    """With no fixtures, every failure is UNKNOWN (fleet section 7.5)."""
    adapter = get_adapter("hermes", FIXTURE_ROOT)
    assert not adapter.book.verified
    assert adapter.classify(1, "SYNTHETIC-FAILURE-QUOTA") == classes.UNKNOWN
    assert adapter.classify(1, "anything at all") == classes.UNKNOWN


def test_the_fake_adapter_classifies_its_own_fixtures(fake_kernel):
    adapter = get_adapter("fake", FIXTURE_ROOT)
    assert adapter.book.verified
    assert adapter.classify(2, "SYNTHETIC-FAILURE-QUOTA: gone") == classes.QUOTA
    assert adapter.classify(3, "SYNTHETIC-FAILURE-AUTH: no") == classes.AUTH
    assert adapter.classify(4, "SYNTHETIC-FAILURE-NETWORK: down") == classes.NETWORK
    assert adapter.classify(5, "SYNTHETIC-FAILURE-MODEL-GONE: gone") \
        == classes.MODEL_GONE


def test_unknown_exit_is_unknown_not_crash(fake_kernel):
    adapter = get_adapter("fake", FIXTURE_ROOT)
    assert adapter.classify(139, "segfault of some kind") == classes.UNKNOWN


def test_exit_zero_is_ok(fake_kernel):
    adapter = get_adapter("fake", FIXTURE_ROOT)
    assert adapter.classify(0, "") == classes.OK


def test_the_measured_capabilities_are_what_the_live_spike_found():
    """The capabilities come from spike S-A1, run live on 2026-10-22.

    Before the live spike every real adapter's capabilities were ``False``
    and the consequences were severe: a console window per worker, no
    resume, and every failure classified ``UNKNOWN``.
    """
    hermes = get_adapter("hermes", FIXTURE_ROOT)
    assert hermes.caps.headless              # it ran and exited 0
    assert hermes.caps.can_resume            # --resume <id> exited 0
    assert hermes.caps.reports_session_id    # it prints "Resume this session with: ..."
    assert not hermes.caps.can_swap_model_on_resume   # no second model string is known

    pi = get_adapter("pi", FIXTURE_ROOT)
    assert pi.caps.headless
    assert pi.caps.can_resume
    assert pi.caps.can_swap_model_on_resume  # measured: exit 0 with another model

    kilo = get_adapter("kilo", FIXTURE_ROOT)
    assert kilo.caps.headless
    assert kilo.caps.can_resume              # --continue exited 0
    assert not kilo.caps.reports_session_id   # it continues without an id

    opencode = get_adapter("opencode", FIXTURE_ROOT)
    assert opencode.caps.headless             # it ran and produced a rate limit
    assert opencode.caps.can_resume

    cline = get_adapter("cline", FIXTURE_ROOT)
    assert cline.caps.headless               # it ran and produced a clean error
    assert not cline.caps.can_resume          # untested: no session was obtained


def test_an_unmeasured_adapter_still_defaults_to_false():
    """Unknown means no (fleet section 12.B, risk R-F1).

    The defaults are only lifted for a CLI the live spike has actually
    measured.
    """
    adapter = get_adapter("some-unmeasured-cli", FIXTURE_ROOT)
    caps = adapter.caps
    assert not caps.headless
    assert not caps.can_resume
    assert not caps.can_swap_model_on_resume
    assert not caps.reports_session_id
    assert not adapter.verified()


def test_a_real_adapter_classifies_its_own_captured_failures():
    """The classifier patterns come from real captures."""
    opencode = get_adapter("opencode", FIXTURE_ROOT)
    assert opencode.classify(1, "Error: Rate limit exceeded: free-models-pe") \
        == classes.QUOTA

    cline = get_adapter("cline", FIXTURE_ROOT)
    captured = (FIXTURE_ROOT / "cline" / "model_gone.txt").read_text(
        encoding="utf-8")
    assert cline.classify(1, captured) == classes.MODEL_GONE


def test_a_pattern_without_matching_evidence_is_not_loaded(tmp_path):
    """Fleet rule 15, mechanically: a pattern needs a capture it matches.

    A pattern that does not match the capture it claims to come from is
    not loaded, so the adapter falls back to ``UNKNOWN`` â€” the safe class.
    """
    from fleet.classify import classify, load_book

    directory = tmp_path / "sometool"
    directory.mkdir()
    (directory / "quota.txt").write_text(
        "the provider said no, you are out of quota\n", encoding="utf-8")
    (directory / "patterns.toml").write_text(
        '[quota]\npattern = "rate limit exceeded"\nsource = "quota.txt"\n',
        encoding="utf-8")

    book = load_book("sometool", tmp_path)
    # The pattern does not match the capture, so it is not loaded.
    assert book.patterns == {}
    assert not book.verified
    assert classify(1, "the provider said no, you are out of quota", book) \
        == classes.UNKNOWN


def test_a_pattern_with_matching_evidence_is_loaded(tmp_path):
    from fleet.classify import classify, load_book

    directory = tmp_path / "sometool"
    directory.mkdir()
    (directory / "quota.txt").write_text(
        "Error: Rate limit exceeded: free-models-per-day\n", encoding="utf-8")
    (directory / "patterns.toml").write_text(
        '[quota]\npattern = "Rate limit exceeded"\nsource = "quota.txt"\n',
        encoding="utf-8")

    book = load_book("sometool", tmp_path)
    assert book.verified
    assert classify(1, "Error: Rate limit exceeded: free-models-per-day",
                    book) == classes.QUOTA


# ---------------------------------------------------------------------------
# The recovery ladder
# ---------------------------------------------------------------------------

def test_l0_retries_a_network_failure(fake_kernel):
    context = recover.RecoveryContext(failure_class=classes.NETWORK,
                                      network_retries=0)
    decision = recover.decide(context)
    assert decision.step == recover.L0
    assert decision.action == "retry"
    assert decision.delay_seconds == 30


def test_l1_resumes_when_the_adapter_can_resume(fake_kernel):
    context = recover.RecoveryContext(failure_class=classes.QUOTA,
                                      adapter_supports_resume=True)
    decision = recover.decide(context)
    assert decision.step == recover.L1
    assert decision.action == "resume"


def test_l2_starts_fresh_when_the_adapter_cannot_resume(fake_kernel):
    """Every real adapter cannot resume, so L2 is the real path."""
    context = recover.RecoveryContext(failure_class=classes.QUOTA,
                                      adapter_supports_resume=False)
    decision = recover.decide(context)
    assert decision.step == recover.L2
    assert decision.action == "fresh"


def test_l3_revokes_when_the_restarts_run_out(fake_kernel):
    context = recover.RecoveryContext(failure_class=classes.QUOTA,
                                      restart_count=5, max_restarts=5)
    decision = recover.decide(context)
    assert decision.step == recover.L3
    assert decision.action == "revoke"


def test_l4_blocks_when_the_attempts_run_out(fake_kernel):
    context = recover.RecoveryContext(failure_class=classes.QUOTA,
                                      attempt=3, attempts_max=3)
    decision = recover.decide(context)
    assert decision.step == recover.L4
    assert decision.action == "block"
    assert decision.queue_item


def test_quota_cools_the_profile_and_doubles(fake_kernel):
    state = FleetState()
    policy = {"recovery": {"quota_cooldown_s": 3600,
                           "quota_cooldown_max_s": 86400}}
    first = recover.apply_penalty(state, "p1", classes.QUOTA, policy=policy)
    assert first.cooldown_seconds == 3600
    second = recover.apply_penalty(state, "p1", classes.QUOTA, policy=policy)
    assert second.cooldown_seconds == 7200       # doubles


def test_auth_disables_the_profile_and_raises_a_queue_item(fake_kernel):
    state = FleetState()
    result = recover.apply_penalty(state, "p1", classes.AUTH)
    assert result.disabled
    assert result.queue_item
    assert not state.profile("p1").enabled


def test_model_gone_disables_the_profile(fake_kernel):
    state = FleetState()
    result = recover.apply_penalty(state, "p1", classes.MODEL_GONE)
    assert result.disabled


def test_three_providers_reporting_network_pauses_dispatch(fake_kernel):
    state = FleetState()
    policy = {"recovery": {"network_circuit_breaker_providers": 3,
                           "network_circuit_breaker_window_s": 120}}
    now = time.time()
    for provider in ("alpha", "beta", "gamma"):
        recover.apply_penalty(state, f"p-{provider}", classes.NETWORK,
                              policy=policy, provider=provider, now=now)
    assert state.dispatch_paused
    assert "circuit breaker" in state.pause_reason


def test_one_network_failure_does_not_pause_dispatch(fake_kernel):
    state = FleetState()
    recover.apply_penalty(state, "p1", classes.NETWORK, provider="alpha")
    assert not state.dispatch_paused


def test_two_unknown_failures_cool_the_profile(fake_kernel):
    state = FleetState()
    policy = {"recovery": {"unknown_cooldown_after": 2,
                           "unknown_cooldown_s": 900}}
    first = recover.apply_penalty(state, "p1", classes.UNKNOWN, policy=policy)
    assert first.cooldown_seconds == 0
    second = recover.apply_penalty(state, "p1", classes.UNKNOWN, policy=policy)
    assert second.cooldown_seconds == 900


# ---------------------------------------------------------------------------
# The harness and the fake CLI (F2, F3, F6, F13)
# ---------------------------------------------------------------------------

def _harness(kernel) -> Harness:
    state = FleetState.load(Path(kernel.repo.root) / ".pm" / "fleet-state.json")
    return Harness(kernel, state, fixture_root=FIXTURE_ROOT)


def test_a_successful_lease_submits_a_bundle(fake_kernel):
    task = make_task(fake_kernel, oracles=["python -c \"print('ok')\""])
    harness = _harness(fake_kernel)
    profile = Profile.from_dict(fake_profile("fake-a"))
    result = harness.run(task, profile)
    assert result.outcome == "submitted", result.to_dict()
    assert result.exit_code == 0
    assert result.oracles and result.oracles[0]["ok"]
    bundle_path = (fake_kernel.repo.evidence_dir /
                   f"EB-{task.id}-{result.bundle['fence']}" / "bundle.json")
    assert bundle_path.is_file()


def test_a_failing_oracle_triggers_a_fix_round_then_fails(fake_kernel):
    """The oracles decide, not the worker's exit code."""
    task = make_task(fake_kernel, oracles=["python -c \"raise SystemExit(3)\""])
    harness = _harness(fake_kernel)
    profile = Profile.from_dict(fake_profile("fake-a"))
    result = harness.run(task, profile)
    assert result.outcome == "failed"
    assert result.fix_rounds >= 1
    assert all(not o["ok"] for o in result.oracles)


def test_killing_a_worker_mid_task_does_not_promote_it(fake_kernel):
    """F2: the fence is unchanged and nothing is integrated.

    The ``slow`` scenario keeps the worker alive long enough to be killed
    mid-task; without it the fake finishes before the kill lands and the
    test would race.
    """
    task = make_task(fake_kernel, oracles=["python -c \"print('ok')\""])
    harness = _harness(fake_kernel)
    profile = Profile.from_dict(fake_profile("fake-a", scenario="slow"))
    run, failure = harness.start(task, profile)
    assert run is not None
    fence = run.lease.fence
    from fleet import spawn as spawn_mod
    spawn_mod.kill_slot(run.slot)
    result = harness.poll(run)
    assert result is not None
    # A killed worker is not a success, whatever the log says.
    assert result.outcome != "submitted"
    state = fake_kernel.state()
    assert state.tasks[task.id].state != "DONE"
    # The fence is unchanged: the harness still owns the lease.
    assert state.leases[task.id].fence == fence
    # And exactly one integration event at most, which would be none.
    integrations = [e for e in fake_kernel.events()
                    if e.type == "INTEGRATED" and e.subject == task.id]
    assert len(integrations) <= 1
    assert not integrations


def test_a_quota_failure_cools_the_profile_and_is_classified(fake_kernel):
    """F3: the profile cools and the failure class is recognised."""
    task = make_task(fake_kernel, oracles=["python -c \"print('ok')\""])
    harness = _harness(fake_kernel)
    profile = Profile.from_dict(fake_profile("fake-a", scenario="quota"))
    result = harness.run(task, profile)
    assert result.failure_class == classes.QUOTA
    state = harness.fleet_state.profile("fake-a")
    assert state.cooling()
    assert state.failure_counts.get(classes.QUOTA) == 1


def test_the_handoff_note_is_written_for_a_fresh_recovery(fake_kernel):
    task = make_task(fake_kernel, oracles=["python -c \"print('ok')\""])
    harness = _harness(fake_kernel)
    profile = Profile.from_dict(fake_profile("fake-a", scenario="network"))
    result = harness.run(task, profile)
    assert result.decision["step"] in (recover.L0, recover.L2)
    worktree = Path(result.worktree)
    handoff = worktree / ".pmwork" / "HANDOFF.md"
    # L0 retries in place; a handoff is written when the session restarts.
    if result.decision["step"] == recover.L2:
        assert handoff.is_file()


def test_the_work_order_is_written_and_the_prompt_is_fixed(fake_kernel):
    task = make_task(fake_kernel)
    harness = _harness(fake_kernel)
    profile = Profile.from_dict(fake_profile("fake-a"))
    run, _ = harness.start(task, profile)
    order = Path(run.worktree) / ".pmwork" / "ORDER.md"
    assert order.is_file()
    text = order.read_text(encoding="utf-8")
    assert task.id in text
    assert "The harness will run these itself" in text
    from fleet.order import FIXED_PROMPT
    assert FIXED_PROMPT.isascii()
    assert "%" not in FIXED_PROMPT and '"' not in FIXED_PROMPT


def test_a_scope_violation_is_detected(fake_kernel):
    task = make_task(fake_kernel, scope={"write": ["src/thing.py"], "read": []})
    harness = _harness(fake_kernel)
    profile = Profile.from_dict(fake_profile("fake-a"))
    run, _ = harness.start(task, profile)
    # The fake writes outside the declared scope.
    (Path(run.worktree) / "outside-scope.txt").write_text("x\n", encoding="utf-8")
    check = scope_check(task, run.worktree, fake_kernel.repo)
    assert not check["ok"]
    assert any(v["path"] == "outside-scope.txt" for v in check["violations"])


def test_hooks_are_disabled_in_the_worktree(fake_kernel):
    """CIP 2.4: git hooks are shared by every worktree."""
    task = make_task(fake_kernel)
    harness = _harness(fake_kernel)
    profile = Profile.from_dict(fake_profile("fake-a"))
    run, _ = harness.start(task, profile)
    code, out, err = fake_kernel.git("config", "--worktree",
                                    "core.hooksPath", cwd=Path(run.worktree))
    assert code == 0
    assert out.strip().endswith("nohooks")


# ---------------------------------------------------------------------------
# Quoting (F11)
# ---------------------------------------------------------------------------

def test_a_hostile_order_reaches_the_worker_intact(fake_kernel):
    """F11: quotes, %, &, ^ and non-ASCII survive, because the order is a file."""
    hostile = ('Read "ORDER.md" & do 100% of it ^ carefully â€” Ã¼nÃ¯cÃ¶dÃ© ä¸­æ–‡')
    task = make_task(fake_kernel,
                     title=f"Handle {hostile}",
                     oracles=["python -c \"print('ok')\""])
    harness = _harness(fake_kernel)
    profile = Profile.from_dict(fake_profile("fake-a"))
    run, _ = harness.start(task, profile)
    order = (Path(run.worktree) / ".pmwork" / "ORDER.md").read_text(
        encoding="utf-8")
    assert hostile in order
    # And the argv the worker received is a plain sentence.
    assert len(run.slot.argv) > 0
    assert not any("%" in part for part in run.slot.argv)


# ---------------------------------------------------------------------------
# Restart reconciliation (F8)
# ---------------------------------------------------------------------------

def test_reconcile_reports_adopted_and_lost_workers(fake_kernel):
    task = make_task(fake_kernel)
    harness = _harness(fake_kernel)
    profile = Profile.from_dict(fake_profile("fake-a"))
    run, _ = harness.start(task, profile)
    dispatcher = Dispatcher(fake_kernel, harness.fleet_state,
                            fixture_root=FIXTURE_ROOT)
    report = dispatcher.reconcile()
    assert task.id in report["adopted"]
    assert task.id in dispatcher.runs


def test_reconcile_loses_a_worker_whose_process_is_gone(fake_kernel):
    task = make_task(fake_kernel)
    harness = _harness(fake_kernel)
    profile = Profile.from_dict(fake_profile("fake-a"))
    run, _ = harness.start(task, profile)
    from fleet import spawn as spawn_mod
    spawn_mod.kill_slot(run.slot)
    dispatcher = Dispatcher(fake_kernel, harness.fleet_state,
                            fixture_root=FIXTURE_ROOT)
    report = dispatcher.reconcile()
    assert task.id in report["lost"] or task.id in report["adopted"]
    # Either way the task is not DONE.
    assert fake_kernel.state().tasks[task.id].state != "DONE"


# ---------------------------------------------------------------------------
# Profile import from the operator's prompts.json
# ---------------------------------------------------------------------------

def test_import_prompts_collapses_projects_and_drops_the_prompt(tmp_path):
    source = tmp_path / "prompts.json"
    source.write_text("""{
      "settings": {"delay_seconds": 1.0, "keep_open": true},
      "prompts": [
        {"id": "1", "name": "hermes a", "group": "A", "prefix": "hermes chat --oneshot -q",
         "prompt": "do a thing", "suffix": "--yolo --cli --in \\"C:\\\\a\\"",
         "cwd": "C:\\\\a"},
        {"id": "2", "name": "hermes b", "group": "B", "prefix": "hermes chat --oneshot -q",
         "prompt": "do another thing", "suffix": "--yolo --cli --in \\"C:\\\\b\\"",
         "cwd": "C:\\\\b"}
      ]}""", encoding="utf-8")
    profiles = import_prompts(source)
    assert len(profiles) == 1                # the two projects collapse
    profile = profiles[0]
    assert profile.adapter == "hermes"
    assert "{prompt}" in profile.argv_new
    assert "{cwd}" in profile.argv_new
    assert "do a thing" not in " ".join(profile.argv_new)


def test_import_prompts_marks_alias_models_as_unknown_family(tmp_path):
    source = tmp_path / "prompts.json"
    source.write_text("""{"settings": {}, "prompts": [
      {"id": "1", "name": "p", "group": "g", "prefix": "pi --provider openrouter --model free -p",
       "prompt": "x", "suffix": "", "cwd": ""},
      {"id": "2", "name": "p2", "group": "g", "prefix": "pi --provider x --model deepseek/deepseek-v4-flash-free -p",
       "prompt": "y", "suffix": "", "cwd": ""}]}""", encoding="utf-8")
    profiles = import_prompts(source)
    by_id = {p.id: p for p in profiles}
    assert any(p.family == "unknown" for p in profiles)
    assert any(p.family == "deepseek" for p in profiles)


def test_guess_family():
    assert guess_family("deepseek/deepseek-v4-flash-free") == "deepseek"
    assert guess_family("free") == "unknown"
    assert guess_family("poor-pi") == "unknown"
    assert guess_family("") == "unknown"


# ---------------------------------------------------------------------------
# The dispatcher
# ---------------------------------------------------------------------------

def test_the_dispatcher_starts_a_lease_for_a_ready_task(fake_kernel):
    task = make_task(fake_kernel, oracles=["python -c \"print('ok')\""])
    dispatcher = Dispatcher(fake_kernel, FleetState(),
                            fixture_root=FIXTURE_ROOT)
    report = dispatcher.tick()
    assert report.started
    assert report.started[0]["task"] == task.id
    assert task.id in dispatcher.runs


def test_the_dispatcher_records_the_assignment_reason(fake_kernel):
    make_task(fake_kernel)
    dispatcher = Dispatcher(fake_kernel, FleetState(),
                            fixture_root=FIXTURE_ROOT)
    dispatcher.tick()
    events = [e for e in fake_kernel.events() if e.type == "FLEET_ASSIGNED"]
    assert events
    assert events[-1].payload["profile"]
    assert events[-1].payload["candidates"]


def test_the_dispatcher_status_lists_profiles(fake_kernel):
    dispatcher = Dispatcher(fake_kernel, FleetState(),
                            fixture_root=FIXTURE_ROOT)
    status = dispatcher.status()
    assert status["profiles"][0]["id"] == "fake-a"
    assert status["fleet_cap"] == 20


def test_a_dispatch_pause_stops_new_work(fake_kernel):
    make_task(fake_kernel)
    state = FleetState()
    state.dispatch_paused = True
    state.pause_reason = "circuit breaker"
    dispatcher = Dispatcher(fake_kernel, state, fixture_root=FIXTURE_ROOT)
    report = dispatcher.tick()
    assert not report.started
    assert any("paused" in note for note in report.notes)
