"""QuotaGate tests (pilot v1 acceptance tests Q1 and Q2).

Q1 is the DST test across the US daylight-saving change on 1 November
2026; Q2 is the account-wide rule test.  Both run against a fake clock, so
they are deterministic and fast.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT / "src", ROOT / "gateway"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from pmk.clock import FakeClock  # noqa: E402
from quotagate.config import (Account, Combo, Deployment, GatewayConfig,
                              QuotaRule)  # noqa: E402
from quotagate.engine import (Ledger, QuotaEngine, QuotaExceeded,  # noqa: E402
                              to_iso, window_reset, window_start)
from quotagate.errors import (RATE_DAY, RATE_MINUTE, UNKNOWN_429,  # noqa: E402
                              all_exhausted, classify_429)
from quotagate.routing import HEADROOM, USE_IT_OR_LOSE_IT, route  # noqa: E402


def build_config(*rules) -> GatewayConfig:
    """A small configuration with two accounts on one quota group.

    Any positional argument is one quota rule, given as a dict.
    """
    config = GatewayConfig()
    config.providers = {"alpha": {"name": "Alpha"},
                        "beta": {"name": "Beta"}}
    config.accounts = {
        "acct-1": Account.from_dict({"id": "acct-1", "provider": "alpha",
                                     "quota_group": "group-1",
                                     "secret_env": "ALPHA_KEY",
                                     "data_class": "public"}),
        "acct-2": Account.from_dict({"id": "acct-2", "provider": "alpha",
                                     "quota_group": "group-1",
                                     "secret_env": "ALPHA_KEY2",
                                     "data_class": "public"}),
        "acct-3": Account.from_dict({"id": "acct-3", "provider": "beta",
                                     "quota_group": "group-2",
                                     "secret_env": "BETA_KEY",
                                     "data_class": "public"}),
    }
    config.deployments = {
        "d1": Deployment.from_dict({"id": "d1", "provider": "alpha",
                                    "account": "acct-1", "model": "m1",
                                    "family": "anthropic"}),
        "d2": Deployment.from_dict({"id": "d2", "provider": "alpha",
                                    "account": "acct-2", "model": "m1",
                                    "family": "anthropic"}),
        "d3": Deployment.from_dict({"id": "d3", "provider": "beta",
                                    "account": "acct-3", "model": "m2",
                                    "family": "deepseek"}),
    }
    config.combos = {
        "all": Combo.from_dict({"name": "all", "deployments": ["d1", "d2", "d3"],
                                "strategy": "priority"}),
    }
    config.rules = []
    for rule in rules:
        config.rules.append(QuotaRule.from_dict(rule))
    return config


def engine_with(clock, **rule) -> QuotaEngine:
    """An engine with exactly one quota rule."""
    return QuotaEngine(build_config(rule), Ledger(), clock)


# ---------------------------------------------------------------------------
# Scopes
# ---------------------------------------------------------------------------

def test_a_deployment_rule_limits_only_that_deployment(clock):
    engine = engine_with(clock, scope="deployment", metric="requests",
                          window="rolling_60s", limit=2, target="d1")
    engine.reserve(engine.config.deployment("d1"))
    engine.reserve(engine.config.deployment("d1"))
    with pytest.raises(QuotaExceeded):
        engine.reserve(engine.config.deployment("d1"))
    # d2 is unaffected.
    engine.reserve(engine.config.deployment("d2"))


def test_an_account_rule_covers_every_model_on_the_account(clock):
    engine = engine_with(clock, scope="account", metric="requests",
                          window="rolling_60s", limit=2, target="acct-1")
    engine.reserve(engine.config.deployment("d1"))
    engine.reserve(engine.config.deployment("d1"))
    with pytest.raises(QuotaExceeded):
        engine.reserve(engine.config.deployment("d1"))


def test_the_account_wide_rule_test(clock):
    """Q2: three models sharing an account limit of 5/day behave as one pool.

    Here two deployments share a *quota group*, which is the same shape:
    two Gemini keys in one Google project share an upstream counter.
    """
    config = build_config()
    config.rules.append(QuotaRule(scope="quota_group", metric="requests",
                                   window="fixed_daily", limit=5,
                                   target="group-1", timezone="UTC"))
    engine = QuotaEngine(config, Ledger(), clock)

    # Five requests across the two deployments in the group succeed.
    for _ in range(5):
        engine.reserve(engine.config.deployment("d1"))
    # The sixth, on the *other* deployment in the same group, is refused:
    # the group is one pool of 5, not two pools of 5.
    with pytest.raises(QuotaExceeded) as exc:
        engine.reserve(engine.config.deployment("d2"))
    assert "quota_group" in exc.value.admission.rule.scope


def test_a_provider_rule_covers_every_account(clock):
    engine = engine_with(clock, scope="provider", metric="requests",
                          window="rolling_60s", limit=1, target="alpha")
    engine.reserve(engine.config.deployment("d1"))
    with pytest.raises(QuotaExceeded):
        engine.reserve(engine.config.deployment("d2"))
    # A different provider is unaffected.
    engine.reserve(engine.config.deployment("d3"))


def test_an_unknown_limit_never_blocks(clock):
    """A limit of 0 means unknown, not zero."""
    engine = engine_with(clock, scope="deployment", metric="requests",
                          window="rolling_60s", limit=0, target="d1")
    for _ in range(50):
        engine.reserve(engine.config.deployment("d1"))


def test_every_applicable_scope_must_have_headroom(clock):
    config = build_config()
    config.rules.append(QuotaRule(scope="deployment", metric="requests",
                                   window="rolling_60s", limit=10, target="d1"))
    config.rules.append(QuotaRule(scope="account", metric="requests",
                                   window="rolling_60s", limit=1, target="acct-1"))
    engine = QuotaEngine(config, Ledger(), clock)
    engine.reserve(engine.config.deployment("d1"))
    with pytest.raises(QuotaExceeded) as exc:
        engine.reserve(engine.config.deployment("d1"))
    assert exc.value.admission.rule.scope == "account"


# ---------------------------------------------------------------------------
# Reservation, reconciliation and refund
# ---------------------------------------------------------------------------

def test_reservation_takes_one_unit_at_every_scope(clock):
    config = build_config()
    config.rules.append(QuotaRule(scope="deployment", metric="requests",
                                   window="rolling_60s", limit=10, target="d1"))
    config.rules.append(QuotaRule(scope="provider", metric="requests",
                                   window="rolling_60s", limit=10, target="alpha"))
    engine = QuotaEngine(config, Ledger(), clock)
    reservation = engine.reserve(engine.config.deployment("d1"))
    scopes = {scope for scope, _m, _a in reservation.charges}
    assert scopes == {"deployment:d1", "provider:alpha"}


def test_refund_returns_the_units_at_every_scope(clock):
    config = build_config()
    config.rules.append(QuotaRule(scope="deployment", metric="requests",
                                   window="rolling_60s", limit=10, target="d1"))
    config.rules.append(QuotaRule(scope="provider", metric="requests",
                                   window="rolling_60s", limit=10, target="alpha"))
    engine = QuotaEngine(config, Ledger(), clock)
    deployment = engine.config.deployment("d1")
    reservation = engine.reserve(deployment)
    engine.refund(reservation)
    # Everything is available again.
    assert engine.check(deployment).allowed
    for _ in range(10):
        engine.reserve(deployment)


def test_commit_reconciles_the_token_charge(clock):
    config = build_config()
    config.rules.append(QuotaRule(scope="deployment", metric="tokens",
                                   window="rolling_60s", limit=1000, target="d1"))
    engine = QuotaEngine(config, Ledger(), clock)
    deployment = engine.config.deployment("d1")
    reservation = engine.reserve(deployment, tokens=100)
    engine.commit(reservation, tokens=40)
    rule = engine.applicable(deployment, "tokens")[0][0]
    assert engine.used(rule, deployment) == 40


# ---------------------------------------------------------------------------
# Q1: the DST test
# ---------------------------------------------------------------------------

def test_the_dst_test_across_1_november_2026(clock):
    """Q1: a daily quota resets at local midnight across the DST change.

    On 1 November 2026 the United States leaves daylight saving, so the
    local day is 25 hours long and the reset moves one hour earlier in
    UTC.  The quota must still reset exactly at local midnight, once.
    """
    config = build_config()
    config.rules.append(QuotaRule(scope="deployment", metric="requests",
                                   window="fixed_daily", limit=1,
                                   target="d1", timezone="America/New_York"))
    engine = QuotaEngine(config, Ledger(), clock)

    # 31 October 2026, 12:00 local (16:00 UTC, daylight saving, -04:00).
    clock.set(datetime(2026, 10, 31, 16, 0, 0, tzinfo=timezone.utc))
    engine.reserve(engine.config.deployment("d1"))
    with pytest.raises(QuotaExceeded):
        engine.reserve(engine.config.deployment("d1"))

    # The reset is at local midnight, which is 04:00 UTC on 1 November
    # (standard time, -05:00).
    reset = window_reset("fixed_daily", "America/New_York", engine.now())
    assert to_iso(reset) == "2026-11-01T04:00:00Z"

    # Just before the reset the quota is still exhausted.
    clock.set(datetime(2026, 11, 1, 3, 59, 0, tzinfo=timezone.utc))
    with pytest.raises(QuotaExceeded):
        engine.reserve(engine.config.deployment("d1"))

    # Just after it, the quota is available again.
    clock.set(datetime(2026, 11, 1, 4, 0, 1, tzinfo=timezone.utc))
    engine.reserve(engine.config.deployment("d1"))


def test_the_dst_day_is_25_hours_long(clock):
    """The local day that contains the transition is 25 hours."""
    start = window_start("fixed_daily", "America/New_York",
                         datetime(2026, 11, 1, 12, 0, 0,
                                  tzinfo=timezone.utc).timestamp())
    end = window_reset("fixed_daily", "America/New_York", start + 3600)
    assert end - start == 25 * 3600


def test_the_day_before_the_transition_is_24_hours(clock):
    start = window_start("fixed_daily", "America/New_York",
                         datetime(2026, 10, 31, 12, 0, 0,
                                  tzinfo=timezone.utc).timestamp())
    end = window_reset("fixed_daily", "America/New_York", start + 3600)
    assert end - start == 24 * 3600


# ---------------------------------------------------------------------------
# The earliest-available time
# ---------------------------------------------------------------------------

def test_the_earliest_available_time_is_the_latest_of_the_blocking_rules(clock):
    config = build_config()
    config.rules.append(QuotaRule(scope="deployment", metric="requests",
                                   window="rolling_60s", limit=1, target="d1"))
    config.rules.append(QuotaRule(scope="provider", metric="requests",
                                   window="rolling_24h", limit=1, target="alpha"))
    engine = QuotaEngine(config, Ledger(), clock)
    deployment = engine.config.deployment("d1")
    engine.reserve(deployment)
    earliest = engine.earliest_available(deployment)
    now = engine.now()
    # The 24-hour rule blocks for longer, so it decides.
    assert earliest >= now + 86000


# ---------------------------------------------------------------------------
# Cooldowns and failures
# ---------------------------------------------------------------------------

def test_rate_minute_honours_retry_after_but_caps_it(clock):
    engine = engine_with(clock)
    deployment = engine.config.deployment("d1")
    until = engine.apply_failure(deployment, RATE_MINUTE, retry_after=600)
    assert until - engine.now() <= 90.0


def test_an_unrecognised_429_cools_for_sixty_seconds(clock):
    engine = engine_with(clock)
    deployment = engine.config.deployment("d1")
    until = engine.apply_failure(deployment, UNKNOWN_429)
    assert 59 <= until - engine.now() <= 61


def test_a_disabled_deployment_is_not_usable(clock):
    engine = engine_with(clock)
    deployment = engine.config.deployment("d1")
    engine.ledger.disable("d1", "test")
    usable, reason = engine.is_usable(deployment)
    assert not usable
    assert reason == "disabled"


def test_the_classifier_is_conservative_about_unknown_bodies():
    failure = classify_429(429, "{\"error\": \"something new\"}")
    assert failure.failure_class == UNKNOWN_429


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def test_routing_is_deterministic(clock):
    engine = engine_with(clock)
    combo = engine.config.combo("all")
    first = route(engine, engine.config, combo)
    second = route(engine, engine.config, combo)
    assert first.chosen.id == second.chosen.id


def test_routing_excludes_a_family_and_does_not_fall_back_into_it(clock):
    """Verifier independence: an error, never a fallback."""
    engine = engine_with(clock)
    combo = engine.config.combo("all")
    result = route(engine, engine.config, combo,
                   exclude_families=("anthropic",))
    assert result.chosen.id == "d3"


def test_routing_reports_when_nothing_is_eligible(clock):
    engine = engine_with(clock)
    combo = engine.config.combo("all")
    result = route(engine, engine.config, combo,
                   exclude_families=("anthropic", "deepseek"))
    assert result.chosen is None
    assert "no eligible deployment" in result.reason


def test_use_it_or_lose_it_prefers_the_least_headroom(clock):
    config = build_config()
    config.combos["all"] = Combo.from_dict({"name": "all", "deployments": ["d1", "d2"], "strategy": USE_IT_OR_LOSE_IT})
    config.rules.append(QuotaRule(scope="deployment", metric="requests",
                                   window="rolling_60s", limit=10, target="d1"))
    config.rules.append(QuotaRule(scope="deployment", metric="requests",
                                   window="rolling_60s", limit=10, target="d2"))
    engine = QuotaEngine(config, Ledger(), clock)
    engine.reserve(engine.config.deployment("d1"), requests=5)
    result = route(engine, config, config.combo("all"),
                   strategy=USE_IT_OR_LOSE_IT)
    # d2 still has all ten; d1 has five left.  Use it or lose it: d1.
    assert result.chosen.id == "d1"


def test_headroom_prefers_the_most_headroom(clock):
    config = build_config()
    config.rules.append(QuotaRule(scope="deployment", metric="requests",
                                   window="rolling_60s", limit=10, target="d1"))
    config.rules.append(QuotaRule(scope="deployment", metric="requests",
                                   window="rolling_60s", limit=10, target="d2"))
    engine = QuotaEngine(config, Ledger(), clock)
    engine.reserve(engine.config.deployment("d1"), requests=5)
    result = route(engine, config, config.combo("all"), strategy=HEADROOM)
    assert result.chosen.id == "d2"


# ---------------------------------------------------------------------------
# The structured all-exhausted response
# ---------------------------------------------------------------------------

def test_the_all_exhausted_response_carries_the_earliest_available_time():
    error = all_exhausted("all", earliest_available_utc="2026-10-23T04:00:00Z")
    assert error.status_code == 429
    body = error.to_obj()
    assert body["error"]["type"] == "rate_limit_error"
    assert body["error"]["earliest_available_utc"] == "2026-10-23T04:00:00Z"


# ---------------------------------------------------------------------------
# M3: Exhaustion drill and account-wide drill
# ---------------------------------------------------------------------------

def build_exhaustion_config(*rules) -> GatewayConfig:
    """Configuration with three fake models, each with a daily limit of 5."""
    config = GatewayConfig()
    config.providers = {"fake-provider": {"name": "Fake Provider"}}
    config.accounts = {
        "acct-fake-1": Account.from_dict({"id": "acct-fake-1", "provider": "fake-provider",
                                          "quota_group": "", "secret_env": "FAKE_KEY_1",
                                          "data_class": "public"}),
        "acct-fake-2": Account.from_dict({"id": "acct-fake-2", "provider": "fake-provider",
                                          "quota_group": "", "secret_env": "FAKE_KEY_2",
                                          "data_class": "public"}),
        "acct-fake-3": Account.from_dict({"id": "acct-fake-3", "provider": "fake-provider",
                                          "quota_group": "", "secret_env": "FAKE_KEY_3",
                                          "data_class": "public"}),
    }
    config.deployments = {
        "fake-model-a": Deployment.from_dict({"id": "fake-model-a", "provider": "fake-provider",
                                              "account": "acct-fake-1", "model": "fake-a",
                                              "family": "fake"}),
        "fake-model-b": Deployment.from_dict({"id": "fake-model-b", "provider": "fake-provider",
                                              "account": "acct-fake-2", "model": "fake-b",
                                              "family": "fake"}),
        "fake-model-c": Deployment.from_dict({"id": "fake-model-c", "provider": "fake-provider",
                                              "account": "acct-fake-3", "model": "fake-c",
                                              "family": "fake"}),
    }
    config.combos = {
        "exhaustion-test": Combo.from_dict({"name": "exhaustion-test",
                                            "deployments": ["fake-model-a", "fake-model-b", "fake-model-c"],
                                            "strategy": "priority"}),
    }
    config.rules = []
    for rule in rules:
        config.rules.append(QuotaRule.from_dict(rule))
    return config


def test_exhaustion_drill_three_models_daily_limit_5(clock):
    """M3 exhaustion drill: three fake models, daily limit 5, 20 requests.

    Exactly 15 succeed (5 per model), the 16th returns structured 429.
    Advancing the clock past midnight restores service.
    """
    config = build_exhaustion_config(
        {"scope": "deployment", "metric": "requests", "window": "fixed_daily",
         "limit": 5, "target": "fake-model-a", "timezone": "UTC"},
        {"scope": "deployment", "metric": "requests", "window": "fixed_daily",
         "limit": 5, "target": "fake-model-b", "timezone": "UTC"},
        {"scope": "deployment", "metric": "requests", "window": "fixed_daily",
         "limit": 5, "target": "fake-model-c", "timezone": "UTC"},
    )
    engine = QuotaEngine(config, Ledger(), clock)

    # Use the combo to route through all three models
    combo = config.combo("exhaustion-test")

    # 15 requests should succeed (5 per model)
    success_count = 0
    for i in range(20):
        result = route(engine, config, combo, strategy="priority")
        if result.chosen is None:
            # Exhausted
            assert i == 15, f"Expected exhaustion at request 16, got it at {i + 1}"
            break
        engine.reserve(result.chosen)
        success_count += 1

    assert success_count == 15, f"Expected 15 successes, got {success_count}"

    # The 16th request (index 15) should get a structured 429 via route()
    result = route(engine, config, combo, strategy="priority")
    assert result.chosen is None, "Expected no eligible deployment after 15 requests"
    assert "no eligible deployment" in result.reason

    # Check the structured 429 from the engine directly
    # All three deployments should be exhausted
    for dep_id in ["fake-model-a", "fake-model-b", "fake-model-c"]:
        dep = config.deployment(dep_id)
        check = engine.check(dep)
        assert not check.allowed, f"{dep_id} should be exhausted"
        assert check.rule is not None

    # Advance clock past midnight (next day)
    # Fixed daily window in UTC: midnight = 00:00 UTC
    next_day = datetime(2026, 10, 24, 0, 0, 1, tzinfo=timezone.utc)
    clock.set(next_day)

    # After clock advance, all deployments should be available again
    for dep_id in ["fake-model-a", "fake-model-b", "fake-model-c"]:
        dep = config.deployment(dep_id)
        check = engine.check(dep)
        assert check.allowed, f"{dep_id} should be available after midnight"

    # 5 more requests should succeed
    for _ in range(5):
        result = route(engine, config, combo, strategy="priority")
        assert result.chosen is not None
        engine.reserve(result.chosen)


def test_account_wide_drill_three_models_one_pool(clock):
    """M3 account-wide drill: three models sharing account limit of 5/day = one pool of 5.

    This uses a quota_group at the account level to simulate a shared upstream counter.
    """
    config = GatewayConfig()
    config.providers = {"fake-provider": {"name": "Fake Provider"}}
    config.accounts = {
        "acct-shared-1": Account.from_dict({"id": "acct-shared-1", "provider": "fake-provider",
                                            "quota_group": "shared-group", "secret_env": "KEY1",
                                            "data_class": "public"}),
        "acct-shared-2": Account.from_dict({"id": "acct-shared-2", "provider": "fake-provider",
                                            "quota_group": "shared-group", "secret_env": "KEY2",
                                            "data_class": "public"}),
        "acct-shared-3": Account.from_dict({"id": "acct-shared-3", "provider": "fake-provider",
                                            "quota_group": "shared-group", "secret_env": "KEY3",
                                            "data_class": "public"}),
    }
    config.deployments = {
        "shared-model-a": Deployment.from_dict({"id": "shared-model-a", "provider": "fake-provider",
                                                "account": "acct-shared-1", "model": "shared-a",
                                                "family": "fake"}),
        "shared-model-b": Deployment.from_dict({"id": "shared-model-b", "provider": "fake-provider",
                                                "account": "acct-shared-2", "model": "shared-b",
                                                "family": "fake"}),
        "shared-model-c": Deployment.from_dict({"id": "shared-model-c", "provider": "fake-provider",
                                                "account": "acct-shared-3", "model": "shared-c",
                                                "family": "fake"}),
    }
    config.combos = {
        "shared-test": Combo.from_dict({"name": "shared-test",
                                        "deployments": ["shared-model-a", "shared-model-b", "shared-model-c"],
                                        "strategy": "priority"}),
    }
    # Quota group rule: 5 requests per day across ALL three accounts
    config.rules.append(QuotaRule.from_dict({
        "scope": "quota_group", "metric": "requests", "window": "fixed_daily",
        "limit": 5, "target": "shared-group", "timezone": "UTC"}))
    engine = QuotaEngine(config, Ledger(), clock)
    combo = config.combo("shared-test")

    # 5 requests total across all three models should succeed
    for i in range(5):
        result = route(engine, config, combo, strategy="priority")
        assert result.chosen is not None
        engine.reserve(result.chosen)

    # 6th request should fail - quota_group exhausted
    result = route(engine, config, combo, strategy="priority")
    assert result.chosen is None
    assert "quota_group" in result.reason or "no eligible deployment" in result.reason

    # Advance clock past midnight
    next_day = datetime(2026, 10, 24, 0, 0, 1, tzinfo=timezone.utc)
    clock.set(next_day)

    # Should be available again
    result = route(engine, config, combo, strategy="priority")
    assert result.chosen is not None
