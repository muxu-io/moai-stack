"""Baseline: all six services healthy and both models pulled.

This is the gate the other paths rely on. When it fails, the messages tell the
operator exactly what to run.
"""

from helpers.preconditions import check_services


def test_stack_ready(cfg):
    problems = check_services(cfg)
    assert not problems, "stack not ready:\n  - " + "\n  - ".join(problems)
