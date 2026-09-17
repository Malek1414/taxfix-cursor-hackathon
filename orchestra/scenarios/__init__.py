"""Scenarios: everything that belongs to one brief, separated from the infrastructure.

A scenario module exports: NAME, TICKETS, make_tools(), agents(registry), steps(), outcome(results, tid),
suite(), compare(actual, expected), mock_responder(models). Tomorrow's brief is a new file next to support.py;
`demo.py --scenario <name>` picks it up. The orchestra does not change.
"""

import importlib


def load(name: str):
    try:
        return importlib.import_module(f"orchestra.scenarios.{name}")
    except ModuleNotFoundError as e:
        raise SystemExit(f"no scenario '{name}' (orchestra/scenarios/{name}.py): {e}") from None
