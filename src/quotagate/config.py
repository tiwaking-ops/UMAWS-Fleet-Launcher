"""QuotaGate configuration (QuotaGate v1.1 sections 3 and 8).

The entities:

``Provider``
    A source of models.
``Account``
    Carries a ``quota_group`` — for example a Google Cloud project — so
    accounts sharing an upstream counter share ours.
``Model``
    A model offered by a provider.
``Deployment``
    The routed unit: **account x model**.
``QuotaRule``
    A limit at one of four scopes.
``Combo``
    An ordered or weighted list of deployments, chosen by the Kernel.

**Limits are configuration, not code.**  A limit of 0 or absent means
*unknown*, not zero.  Free-model status is ``unknown`` until proven, and
unknown-cost models are excluded from free combos.

Secrets are **not** part of the pinned file; they live in a separate
untracked file or in the environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Quota scopes (QuotaGate v1.1 section 3).
SCOPE_DEPLOYMENT = "deployment"
SCOPE_ACCOUNT = "account"
SCOPE_QUOTA_GROUP = "quota_group"
SCOPE_PROVIDER = "provider"
SCOPES = (SCOPE_DEPLOYMENT, SCOPE_ACCOUNT, SCOPE_QUOTA_GROUP, SCOPE_PROVIDER)

# Metrics.
METRIC_REQUESTS = "requests"
METRIC_TOKENS = "tokens"
METRICS = (METRIC_REQUESTS, METRIC_TOKENS)

# Window types (QuotaGate v1.1 section 3).
WINDOW_ROLLING_60S = "rolling_60s"
WINDOW_ROLLING_24H = "rolling_24h"
WINDOW_FIXED_DAILY = "fixed_daily"
WINDOW_FIXED_MONTHLY = "fixed_monthly"
WINDOW_FIXED_INTERVAL = "fixed_interval"
WINDOWS = (WINDOW_ROLLING_60S, WINDOW_ROLLING_24H, WINDOW_FIXED_DAILY,
           WINDOW_FIXED_MONTHLY, WINDOW_FIXED_INTERVAL)


@dataclass(frozen=True)
class QuotaRule:
    """One limit, at one scope."""

    scope: str
    metric: str
    window: str
    limit: int
    target: str = ""                 # the deployment, account, group or provider
    timezone: str = "UTC"            # for fixed_daily and fixed_monthly
    interval_seconds: int = 0        # for fixed_interval
    reset_at: str = ""               # an explicit reset time, if the provider gives one

    @property
    def known(self) -> bool:
        """A limit of 0 or absent means *unknown*, not zero."""
        return self.limit > 0

    def to_dict(self) -> dict:
        return {"scope": self.scope, "metric": self.metric,
                "window": self.window, "limit": self.limit,
                "target": self.target, "timezone": self.timezone,
                "interval_seconds": self.interval_seconds,
                "reset_at": self.reset_at}

    @classmethod
    def from_dict(cls, obj: dict) -> "QuotaRule":
        return cls(
            scope=str(obj.get("scope", SCOPE_DEPLOYMENT)),
            metric=str(obj.get("metric", METRIC_REQUESTS)),
            window=str(obj.get("window", WINDOW_ROLLING_60S)),
            limit=int(obj.get("limit", 0)),
            target=str(obj.get("target", "")),
            timezone=str(obj.get("timezone", "UTC")),
            interval_seconds=int(obj.get("interval_seconds", 0)),
            reset_at=str(obj.get("reset_at", "")),
        )


@dataclass(frozen=True)
class Account:
    id: str
    provider: str
    quota_group: str = ""
    secret_env: str = ""              # the environment variable holding the key
    data_class: str = "public"

    def to_dict(self) -> dict:
        return {"id": self.id, "provider": self.provider,
                "quota_group": self.quota_group, "secret_env": self.secret_env,
                "data_class": self.data_class}

    @classmethod
    def from_dict(cls, obj: dict) -> "Account":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in obj.items() if k in known})


@dataclass(frozen=True)
class Deployment:
    """The routed unit: account x model."""

    id: str
    provider: str
    account: str
    model: str
    family: str = "unknown"
    free: str = "unknown"             # unknown until proven
    data_class: str = "public"
    context_window: int = 0
    supports_tools: bool = False
    combo: str = ""

    def to_dict(self) -> dict:
        return {"id": self.id, "provider": self.provider,
                "account": self.account, "model": self.model,
                "family": self.family, "free": self.free,
                "data_class": self.data_class,
                "context_window": self.context_window,
                "supports_tools": self.supports_tools, "combo": self.combo}

    @classmethod
    def from_dict(cls, obj: dict) -> "Deployment":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in obj.items() if k in known})


@dataclass(frozen=True)
class Combo:
    """An ordered list of deployments."""

    name: str
    deployments: list = field(default_factory=list)
    strategy: str = "use-it-or-lose-it"
    free_only: bool = False

    def to_dict(self) -> dict:
        return {"name": self.name, "deployments": list(self.deployments),
                "strategy": self.strategy, "free_only": self.free_only}

    @classmethod
    def from_dict(cls, obj: dict) -> "Combo":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in obj.items() if k in known})


@dataclass
class GatewayConfig:
    """The whole pinned configuration."""

    providers: dict = field(default_factory=dict)
    accounts: dict = field(default_factory=dict)
    deployments: dict = field(default_factory=dict)
    combos: dict = field(default_factory=dict)
    rules: list = field(default_factory=list)
    data_classes: list = field(default_factory=lambda: ["public", "internal"])
    strategy: str = "use-it-or-lose-it"

    # -- loading ----------------------------------------------------------
    @classmethod
    def load(cls, path: str | Path) -> "GatewayConfig":
        """Load a TOML configuration.

        Read with ``utf-8-sig``: the operator edits with PowerShell, whose
        ``Set-Content -Encoding utf8`` writes a BOM, and ``tomllib`` rejects
        one.
        """
        import tomllib
        from pmk.plat import read_text

        target = Path(path)
        data = tomllib.loads(read_text(target))

        config = cls()
        for key, obj in (data.get("provider") or {}).items():
            config.providers[key] = dict(obj)
        for key, obj in (data.get("account") or {}).items():
            config.accounts[key] = Account.from_dict({"id": key, **obj})
        for key, obj in (data.get("deployment") or {}).items():
            config.deployments[key] = Deployment.from_dict({"id": key, **obj})
        for key, obj in (data.get("combo") or {}).items():
            config.combos[key] = Combo.from_dict({"name": key, **obj})
        for obj in (data.get("quota_rule") or []):
            config.rules.append(QuotaRule.from_dict(obj))
        config.data_classes = list(data.get("data_classes")
                                   or config.data_classes)
        config.strategy = str(data.get("strategy", config.strategy))
        return config

    def to_dict(self) -> dict:
        return {
            "providers": self.providers,
            "accounts": {k: v.to_dict() for k, v in self.accounts.items()},
            "deployments": {k: v.to_dict() for k, v in self.deployments.items()},
            "combos": {k: v.to_dict() for k, v in self.combos.items()},
            "rules": [r.to_dict() for r in self.rules],
            "data_classes": list(self.data_classes),
            "strategy": self.strategy,
        }

    def config_hash(self) -> str:
        """The SHA-256 of the canonical pinned configuration.

        The gateway exposes this at ``GET /v1/quotagate/config-hash`` and
        refuses to start if it does not match the value the Kernel
        publishes (QuotaGate v1.1 section 8).
        """
        import hashlib
        from pmk.events import canonical_json
        return hashlib.sha256(canonical_json(self.to_dict()).encode("utf-8")).hexdigest()

    # -- lookups ----------------------------------------------------------
    def deployment(self, deployment_id: str) -> Deployment | None:
        return self.deployments.get(deployment_id)

    def account(self, account_id: str) -> Account | None:
        return self.accounts.get(account_id)

    def combo(self, name: str) -> Combo | None:
        return self.combos.get(name)

    def rules_for(self, deployment: Deployment) -> list[QuotaRule]:
        """Every rule that applies to *deployment*, at every scope.

        A request must satisfy **all** of them.
        """
        account = self.accounts.get(deployment.account)
        quota_group = account.quota_group if account else ""
        out = []
        for rule in self.rules:
            if rule.scope == SCOPE_DEPLOYMENT and rule.target == deployment.id:
                out.append(rule)
            elif rule.scope == SCOPE_ACCOUNT and rule.target == deployment.account:
                out.append(rule)
            elif (rule.scope == SCOPE_QUOTA_GROUP and quota_group
                  and rule.target == quota_group):
                out.append(rule)
            elif rule.scope == SCOPE_PROVIDER and rule.target == deployment.provider:
                out.append(rule)
        return out

    def scope_key(self, rule: QuotaRule, deployment: Deployment) -> str:
        """The ledger key a unit is charged to for this rule."""
        if rule.scope == SCOPE_DEPLOYMENT:
            return f"deployment:{deployment.id}"
        if rule.scope == SCOPE_ACCOUNT:
            return f"account:{deployment.account}"
        if rule.scope == SCOPE_QUOTA_GROUP:
            account = self.accounts.get(deployment.account)
            return f"quota_group:{account.quota_group if account else ''}"
        return f"provider:{deployment.provider}"

    def deployments_in_combo(self, combo: Combo) -> list[Deployment]:
        return [self.deployments[d] for d in combo.deployments
                if d in self.deployments]
