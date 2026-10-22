"""The template-driven adapter for the real CLIs (hermes, kilo, cline, pi,
opencode).

Every real CLI on the operator's machine is invoked the same way: an argv
template from the profile, with ``{prompt}``, ``{cwd}``, ``{session}`` and
``{model}`` substituted.  There is no per-CLI special casing, because there
is no observed per-CLI behaviour to special case yet (spike S-A1 was
metadata-only by the operator's decision).

**Capabilities are all ``False``.**  The consequences are deliberate:

* ``headless = False`` — the Fleet opens a console window for these
  adapters and marks them ``degraded`` in the Console, because whether they
  can run a full task without a TTY has not been observed.
* ``can_resume = False`` — the recovery ladder cannot resume a session on
  another model, so it falls to L2 (a fresh session with a handoff note) and
  then L3.
* ``reports_session_id = False`` — no session id is extracted.

When a live capture happens, the fix is to fill in ``Caps`` and add
fixture patterns — not to change the harness.
"""

from __future__ import annotations

from .base import BaseAdapter


class TemplateAdapter(BaseAdapter):
    """An adapter driven entirely by the profile's argv template."""

    name = "generic"

    def __init__(self, adapter_name: str = "generic",
                 fixture_root=None):
        super().__init__(fixture_root)
        self.name = adapter_name

    def verified(self) -> bool:
        return False


#: The real adapters.  All of them share the template behaviour; they are
#: separate objects so that a capture can give one of them different
#: capabilities without touching the others.
REAL_ADAPTERS = ("hermes", "kilo", "cline", "pi", "opencode")


def make_real_adapter(name: str, fixture_root=None) -> TemplateAdapter:
    return TemplateAdapter(name, fixture_root=fixture_root)
