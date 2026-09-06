from __future__ import annotations

from keprix.crm.website_scoring import check_rank, score_website


def test_http_page_reports_named_weakness() -> None:
    html = b"<html><head><title>Example</title></head><body>Contact us</body></html>"
    result = score_website("http://example.test", fetcher=lambda _url: (200, {}, html))
    assert 1 <= result["score"] <= 10
    assert result["weakness"] == "no HTTPS"


def test_rank_only_accepts_domain_in_search_results() -> None:
    result = check_rank(
        "example.test",
        "plumbers",
        searcher=lambda _query: [
            {"url": "https://one.test"},
            {"url": "https://www.example.test/page"},
        ],
    )
    assert result == {"ranks_top3": True, "position": 2}


def test_rank_backend_failure_does_not_fabricate_position() -> None:
    result = check_rank("example.test", "plumbers", searcher=lambda _query: (_ for _ in ()).throw(RuntimeError("down")))
    assert result["ranks_top3"] is False
    assert result["position"] is None
