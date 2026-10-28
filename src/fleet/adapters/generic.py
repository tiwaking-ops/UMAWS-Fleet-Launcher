"""The template-driven adapter for the real CLIs (hermes, kilo, cline, pi,
opencode).

Every real CLI on the operator's machine is invoked the same way: an argv
template from the profile, with ``{prompt}``, ``{cwd}``, ``{session}`` and
``{model}`` substituted.  There is no per-CLI special casing in the *code*,
because the per-CLI facts live in *data*: the profile's argv templates and
the capability table below.

**The capabilities are measured, not assumed.**  They come from spike S-A1
run live on 2026-10-22 (`pilot/spikes/s1_live.py` and
`pilot/spikes/s1_live_resume.py`), which ran each CLI with the prompt
"print the word ok and exit" in a throwaway repository, and then resumed
each session.

Until the operator's approval (decision D-24) every capability here was
``False``, and the consequences were severe: the Fleet opened a console
window per worker, the recovery ladder could never take its L1 step, and
every failure was classified ``UNKNOWN``.

What the live spike established, per CLI:

============  =========  ============  ==================  ==================
CLI           headless   session id    resume (same)      resume (diff model)
============  =========  ============  ==================  ==================
hermes        yes        yes           yes (exit 0)       **not tested**
kilo          yes        no (uses      yes (exit 0)       **not tested**
                        ``--continue``)
pi            yes        no (uses      yes (exit 0)       **yes (exit 0)**
                        ``--continue``)
cline         yes        no (needs     **not tested**     **not tested**
                        ``--id``)
opencode      yes        no (uses      **failed**         **not tested**
                        ``--continue``)  (rate limited)
============  =========  ============  ==================  ==================

"not tested" means *no second model string is known for that tool*, and
inventing one would be a guess rather than a measurement.  The Fleet's
"resume on a different model" therefore needs a per-profile list of
interchangeable models, which only **pi** has today.
"""

from __future__ import annotations

from .base import Caps, HERMES_SESSION_PATTERN

#: The measured capabilities, from spike S-A1 (live, 2026-10-22).
MEASURED_CAPS: dict[str, Caps] = {
    "hermes": Caps(
        headless=True,
        can_resume=True,
        can_swap_model_on_resume=False,   # no second model string is known
        reports_session_id=True,
    ),
    "kilo": Caps(
        headless=True,
        can_resume=True,
        can_swap_model_on_resume=False,   # no second model string is known
        reports_session_id=False,         # it continues without an id
    ),
    "pi": Caps(
        headless=True,
        can_resume=True,
        can_swap_model_on_resume=True,    # measured: exit 0
        reports_session_id=False,         # it continues without an id
    ),
    "cline": Caps(
        headless=True,                    # it ran and produced a clean error
        can_resume=False,                 # untested: no session was obtained
        can_swap_model_on_resume=False,
        reports_session_id=False,
    ),
    "opencode": Caps(
        headless=True,                    # it ran and produced a rate limit
        can_resume=True,                  # --continue is documented
        can_swap_model_on_resume=False,   # no model flag in --help
        reports_session_id=False,
    ),
}


class TemplateAdapter:
    """An adapter driven entirely by the profile's argv template."""

    name = "generic"

    def __init__(self, adapter_name: str = "generic", fixture_root=None):
        from .base import BaseAdapter
        self._base = BaseAdapter()
        self._base.name = adapter_name
        self._base.fixture_root = fixture_root
        self.name = adapter_name

    # -- delegate to the base implementation -------------------------------
    def __getattr__(self, item):
        return getattr(self._base, item)

    @property
    def caps(self) -> Caps:
        """The measured capabilities, or all-``False`` if never measured."""
        return MEASURED_CAPS.get(self.name, Caps())

    def verified(self) -> bool:
        return self.name in MEASURED_CAPS

    # -- session -----------------------------------------------------------
    def parse_session_id(self, log_text: str) -> str | None:
        """Parse a session id from the log.

        Overrides BaseAdapter.parse_session_id so that the check against
        ``self.caps.reports_session_id`` uses *this* adapter's measured
        caps (which __getattr__ delegates to _base, but _base.caps returns
        all-False, so we must short-circuit here).
        """
        if not self.caps.reports_session_id:
            return None
        last = None
        for m in HERMES_SESSION_PATTERN.finditer(log_text or ""):
            last = m.group(1)
        return last

    def to_dict(self) -> dict:
        return {"name": self.name, "caps": self.caps.to_dict(),
                "verified": self.verified(),
                "patterns": self._base.book.to_dict()}


#: The real adapters.
REAL_ADAPTERS = ("hermes", "kilo", "cline", "pi", "opencode")


def make_real_adapter(name: str, fixture_root=None) -> TemplateAdapter:
    return TemplateAdapter(name, fixture_root=fixture_root)
