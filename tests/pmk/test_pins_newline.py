"""``write_pins`` writes LF line endings on every platform.

``.pm/pins.sha256`` is ``text eol=lf`` in ``.gitattributes``; ``Path.write_text``
without ``newline="\\n"`` writes CRLF on Windows and leaves the tracked file dirty.
"""

from __future__ import annotations

from pmk.policy import check_pins, write_pins
from pmk.store import Repo


def test_write_pins_writes_lf_only(tmp_path):
    repo = Repo(tmp_path / "repo")
    repo.ensure_layout()
    pm = repo.root / ".pm"
    pm.mkdir(parents=True, exist_ok=True)
    (pm / "constitution.md").write_text("constitution\n", encoding="utf-8", newline="\n")
    (pm / "policy.toml").write_text('version = "p-test"\n', encoding="utf-8", newline="\n")

    path = write_pins(repo)
    data = path.read_bytes()

    assert b"\r" not in data
    assert data.count(b"\n") == 2
    assert check_pins(repo)["ok"] is True
