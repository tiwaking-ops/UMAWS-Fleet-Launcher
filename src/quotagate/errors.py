"""Failure classes and the structured error body (QuotaGate v1.1 sections 3
and 7.4).

The classifier is designed against **captured real responses** (milestone
M1), not guesses.  Until a capture exists, every 429 is
``unknown_429`` and the behaviour is the conservative one.

Failure classes:

``rate_minute``
    Per-minute limit.  Honour ``Retry-After``, capped at about 90 s.
``rate_day``
    Daily limit.  Cool down until the next reset of the blocking rule.
``no_quota``
    No quota at all.  Disable the deployment.
``transient``
    Backoff 5 s, 15 s, 45 s, up to 5 minutes.
``auth``
    Disable the account.
``model_gone``
    Mark the model dead.
``client_error``
    No cooldown: the request was wrong, not the provider.
``unknown_429``
    60-second cooldown, and log the raw body.

The all-exhausted response is HTTP 429 with a structured body that carries
``earliest_available_utc``, so the Kernel scheduler can requeue with a
not-before time instead of failing the task.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

RATE_MINUTE = "rate_minute"
RATE_DAY = "rate_day"
NO_QUOTA = "no_quota"
TRANSIENT = "transient"
AUTH = "auth"
MODEL_GONE = "model_gone"
CLIENT_ERROR = "client_error"
UNKNOWN_429 = "unknown_429"

FAILURE_CLASSES = (RATE_MINUTE, RATE_DAY, NO_QUOTA, TRANSIENT, AUTH,
                   MODEL_GONE, CLIENT_ERROR, UNKNOWN_429)

#: The backoff ladder for transient failures.
TRANSIENT_BACKOFF = (5, 15, 45, 135, 300)

#: ``Retry-After`` is honoured up to this many seconds.
RETRY_AFTER_CAP = 90

#: The cooldown for an unrecognised 429.
UNKNOWN_429_COOLDOWN = 60


@dataclass
class Failure:
    """One classified failure."""

    failure_class: str
    retry_after: float | None = None
    reason: str = ""
    raw_status: int | None = None
    raw_body: str = ""

    def to_dict(self) -> dict:
        return {"failure_class": self.failure_class,
                "retry_after": self.retry_after,
                "reason": self.reason,
                "raw_status": self.raw_status}


@dataclass
class StructuredError:
    """The body of an error response.

    The shape is the same for every error, so a client never has to guess:
    ``error.type`` says what happened and ``error.earliest_available_utc``
    says when to try again, if that is known.
    """

    message: str
    error_type: str = "api_error"
    param: str = ""
    code: str = ""
    earliest_available_utc: str | None = None
    deployment: str = ""
    attempts: list = field(default_factory=list)

    def to_obj(self) -> dict:
        obj = {
            "error": {
                "message": self.message,
                "type": self.error_type,
                "param": self.param,
                "code": self.code,
            }
        }
        if self.earliest_available_utc:
            obj["error"]["earliest_available_utc"] = self.earliest_available_utc
        if self.deployment:
            obj["error"]["deployment"] = self.deployment
        if self.attempts:
            obj["error"]["attempts"] = self.attempts
        return obj

    def to_json(self) -> str:
        return json.dumps(self.to_obj(), ensure_ascii=False)

    @property
    def status_code(self) -> int:
        if self.error_type in ("rate_limit_error", "quota_exceeded"):
            return 429
        if self.error_type == "authentication_error":
            return 401
        if self.error_type == "not_found_error":
            return 404
        if self.error_type == "invalid_request_error":
            return 400
        return 500


def all_exhausted(combo: str, earliest_available_utc: str | None = None,
                  attempts: list | None = None) -> StructuredError:
    """The all-exhausted response (QuotaGate v1.1 section 7.4)."""
    error = StructuredError(
        message=(f"No deployment in combo {combo!r} has quota right now."),
        error_type="rate_limit_error",
        code="no_eligible_deployment",
        earliest_available_utc=earliest_available_utc,
        attempts=list(attempts or []),
    )
    return error


def classify_429(status: int, body: str, headers: dict | None = None) -> Failure:
    """Classify a 429.

    **This is a heuristic until the live capture (milestone M1) provides
    real bodies.**  It is deliberately conservative: an unrecognised body
    becomes ``unknown_429``, which cools for 60 seconds and logs the raw
    body.  It never guesses a specific provider's shape.
    """
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    text = (body or "").lower()
    retry_after = _parse_retry_after(headers.get("retry-after"))

    if "quota" in text and ("exceeded" in text or "insufficient" in text):
        return Failure(RATE_DAY, retry_after, "quota exceeded", status, body)
    if "rate limit" in text or "rate_limit" in text or "too many requests" in text:
        return Failure(RATE_MINUTE, retry_after, "rate limited", status, body)
    if "daily" in text or "per day" in text or "per-day" in text:
        return Failure(RATE_DAY, retry_after, "daily limit", status, body)
    if "per minute" in text or "rpm" in text:
        return Failure(RATE_MINUTE, retry_after, "per-minute limit", status, body)
    return Failure(UNKNOWN_429, retry_after, "unrecognised 429 body", status, body)


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return min(float(value), RETRY_AFTER_CAP)
    except (TypeError, ValueError):
        return None
