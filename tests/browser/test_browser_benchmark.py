"""Browser benchmark tests."""

from keprix.browser.benchmark_runner import get_benchmark_runner


def test_fill_no_submit_benchmark_requires_approval() -> None:
    runner = get_benchmark_runner()
    result = runner.run("fill_no_submit", workspace_id="bench-ws")
    assert result.success is True
    assert result.trace_id
    assert result.screenshot_ids


def test_download_benchmark_gates_approval() -> None:
    result = get_benchmark_runner().run("download_file", workspace_id="bench-ws")
    assert result.success is True
    stored = get_benchmark_runner().get_result(result.trace_id)
    assert stored is not None
    assert stored.benchmark_id == "download_file"


def test_benchmark_results_include_trace_and_screenshots() -> None:
    runner = get_benchmark_runner()
    assert len(runner.list_benchmarks()) >= 6
    result = runner.run("form_fill", workspace_id="bench-ws")
    assert result.success is True
    assert result.trace_id
    assert result.screenshot_ids
    assert get_benchmark_runner().get_result(result.trace_id) is not None


def test_unknown_benchmark_raises() -> None:
    try:
        get_benchmark_runner().run("not-real")
        assert False, "expected KeyError"
    except KeyError:
        pass
