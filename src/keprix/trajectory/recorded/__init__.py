"""Recorded-session / snapshot tests on top of trajectory replay (prompt 772).

Load checked-in trajectory fixtures, replay with recorded results only, and
assert Soft Wall / tool-order / mutation structure without live LLM calls.
"""

from __future__ import annotations

from keprix.trajectory.recorded.fixture import (
    FixtureValidationError,
    RecordedFixture,
    load_fixture,
    scrub_fixture_dict,
    write_fixture,
)
from keprix.trajectory.recorded.harness import (
    ReplayReport,
    assert_fixture_expectations,
    export_recorded_fixture,
    run_recorded_fixture,
)

__all__ = [
    "FixtureValidationError",
    "RecordedFixture",
    "ReplayReport",
    "assert_fixture_expectations",
    "export_recorded_fixture",
    "load_fixture",
    "run_recorded_fixture",
    "scrub_fixture_dict",
    "write_fixture",
]
