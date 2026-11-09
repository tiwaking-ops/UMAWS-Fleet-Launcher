"""The canary dry run: fail at the base, pass on a scratch implementation.

No lease is claimed and no task transitions; the only side effect is a pair
of detached worktrees, removed before the call returns.
"""

from __future__ import annotations

import json
import sys

from fleet import precheck
from pmk import cli

from _fleet_fixtures import make_task

PY = f'"{sys.executable}"'
ORACLE = (
    f'{PY} -c "import pathlib, sys; '
    'sys.exit(0 if pathlib.Path(\'canary.txt\').is_file() else 1)"'
)

PATCH = """diff --git a/canary.txt b/canary.txt
new file mode 100644
--- /dev/null
+++ b/canary.txt
@@ -0,0 +1 @@
+ready
"""


def _canary_task(kernel):
    return make_task(kernel, oracles=[ORACLE],
                     scope={"write": ["canary.txt"], "read": []})


def _patch(tmp_path):
    target = tmp_path / "canary.patch"
    target.write_text(PATCH, encoding="utf-8")
    return target


def test_a_patch_can_validate_a_canary(kernel, tmp_path):
    report = precheck.dry_run(kernel, _canary_task(kernel),
                              patch=_patch(tmp_path))

    assert report["base"]["all_pass"] is False
    assert report["base"]["oracles"][0]["ok"] is False
    assert report["scratch"]["all_pass"] is True
    assert report["canary_valid"] is True


def test_an_already_satisfied_card_is_not_a_canary(kernel):
    task = make_task(kernel, oracles=[f'{PY} -c "import sys"'])

    report = precheck.dry_run(kernel, task)

    assert report["base"]["all_pass"] is True
    assert report["canary_valid"] is False
    assert "already satisfies" in report["reason"]


def test_without_a_scratch_implementation_the_verdict_is_no(kernel):
    report = precheck.dry_run(kernel, _canary_task(kernel))

    assert report["canary_valid"] is False
    assert "no scratch implementation" in report["reason"]


def test_a_patch_that_does_not_apply_is_an_error(kernel, tmp_path):
    bad = tmp_path / "bad.patch"
    bad.write_text("this is not a patch\n", encoding="utf-8")

    report = precheck.dry_run(kernel, _canary_task(kernel), patch=bad)

    assert "did not apply" in report["error"]
    code, out, _ = kernel.repo.git("worktree", "list", "--porcelain")
    assert code == 0
    assert "pmk-precheck-dry" not in out


def test_cli_reports_the_dry_run_as_json(kernel, tmp_path, capsys):
    task = _canary_task(kernel)
    patch = _patch(tmp_path)

    code = cli.main(["--root", str(kernel.repo.root), "task", "precheck",
                     task.id, "--patch", str(patch)])
    report = json.loads(capsys.readouterr().out)

    assert code == 0
    assert report["task"] == task.id
    assert report["canary_valid"] is True
