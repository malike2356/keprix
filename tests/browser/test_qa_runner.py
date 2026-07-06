"""QA runner tests."""

from keprix.browser.action_engine import ActionEngine
from keprix.browser.drivers import StubBrowserDriver
from keprix.browser.qa_runner import BrowserQaRunner


def test_gherkin_scenario_runs_steps() -> None:
    engine = ActionEngine()
    runner = BrowserQaRunner(engine)
    scenario = "\n".join(
        [
            "Given I open https://example.com",
            "Then I take a screenshot",
        ]
    )
    report = runner.run_scenario(scenario, url="about:blank")
    assert report.passed
    assert len(report.steps) == 2
    assert report.steps[0].status == "passed"
    assert report.steps[1].status == "passed"
