"""A failed gate must leave enough evidence to be diagnosed.

T-0148 was requeued with `pytest -q` exit 1 and nothing else; reconstructing
why took a full afternoon of archaeology.  These tests pin the diagnostics.
"""

from fleet.merge import _gate_diagnostics


def test_records_failing_tests_and_tails():
    stdout = "\n".join([
        "....................F..",
        "=========================== short test summary info ===========================",
        "FAILED tests/test_coverage.py::test_counts - AssertionError: 66 != 69",
        "1 failed, 506 passed in 191.4s",
    ])
    diag = _gate_diagnostics(stdout, "some stderr noise\n")
    assert diag["failed_tests"] == [
        "FAILED tests/test_coverage.py::test_counts - AssertionError: 66 != 69"
    ]
    assert diag["stdout_tail"][-1] == "1 failed, 506 passed in 191.4s"
    assert diag["stderr_tail"] == ["some stderr noise"]


def test_blank_output_yields_empty_fields():
    diag = _gate_diagnostics("", "")
    assert diag == {"failed_tests": [], "stdout_tail": [], "stderr_tail": []}


def test_tails_are_bounded():
    stdout = "\n".join(f"line {i}" for i in range(500))
    diag = _gate_diagnostics(stdout, "", lines=40)
    assert len(diag["stdout_tail"]) == 40
    assert diag["stdout_tail"][-1] == "line 499"
