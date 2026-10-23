"""A policy the Kernel cannot read must stop the line.

Regression tests for the defect recorded at the F7 close-out (found when
the drill's own gate was written as invalid TOML and ``load_policy``
silently substituted the defaults, changing the gate to ``pytest -q``
with no warning anywhere).  Fixed 2026-10-24: present-but-unreadable
raises ``PolicyError``, surfaced as ``KernelError("policy_invalid")`` on
every Kernel surface -- including any event append, because every event
is stamped with the policy hash.
"""

from __future__ import annotations

import pytest

from pmk.api import Kernel, KernelError
from pmk.clock import FakeClock
from pmk.policy import PolicyError, load_policy


INVALID_TOML = 'version = p-2026-10-24-bad\n'      # bareword: not valid TOML


def test_an_invalid_policy_refuses_to_load(repo):
    """``load_policy`` raises instead of returning the defaults."""
    repo.policy_path.write_text(INVALID_TOML, encoding="utf-8")
    with pytest.raises(PolicyError) as excinfo:
        load_policy(repo)
    assert "invalid TOML" in str(excinfo.value)
    assert "policy.toml" in str(excinfo.value)


def test_an_invalid_policy_surfaces_as_a_kernel_error(repo):
    """``kernel.policy()`` is the refusal every surface sees."""
    repo.policy_path.write_text(INVALID_TOML, encoding="utf-8")
    kernel = Kernel(root=repo.root, clock=FakeClock())
    with pytest.raises(KernelError) as excinfo:
        kernel.policy()
    assert excinfo.value.reason == "policy_invalid"
    assert "invalid TOML" in str(excinfo.value.details["detail"])


def test_the_kernel_refuses_to_init_under_an_invalid_policy(repo):
    """The first event is stamped with the policy hash, so init refuses.

    A Kernel that cannot state which policy is in force must not write
    the log as if it could.  (The CLI renders this as
    ``{"error": "policy_invalid", ...}`` with exit 2.)
    """
    repo.policy_path.write_text(INVALID_TOML, encoding="utf-8")
    kernel = Kernel(root=repo.root, clock=FakeClock())
    with pytest.raises(KernelError) as excinfo:
        kernel.init()
    assert excinfo.value.reason == "policy_invalid"


def test_a_missing_policy_file_still_defaults(repo):
    """First-boot behaviour is unchanged: absent file means defaults.

    The refusal is only for a file that exists but cannot be read -- the
    ``pmk init`` flow (and every test fixture) runs before a policy
    exists.
    """
    assert not repo.policy_path.is_file()
    kernel = Kernel(root=repo.root, clock=FakeClock())
    assert kernel.policy()["gate"]["cmd"] == "pytest -q"
