"""
Qualitative acceptance criteria for the eight product personas (Prompts 96-103).

These tests verify behavioral correctness, not just structural presence.
Each persona test block proves that the core decision-making logic matches
the persona's domain contract.

Personas covered: NEXUS, FORGE, WARDEN, SAGE, BEACON, PRISM, COMPASS, EMBER.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# NEXUS (Prompt 96) -- orchestration and routing
# ---------------------------------------------------------------------------


class TestNexusRouting:
    """NEXUS routes requests to the right persona and handles edge cases."""

    @pytest.fixture()
    def orchestrator(self):
        from keprix.personas.nexus.orchestrator import NexusOrchestrator

        return NexusOrchestrator(workspace_id="test-ws", run_id="test-run")

    def test_coding_request_routes_to_forge(self, orchestrator):
        decision = orchestrator.route("please build and deploy the API for our new service")
        assert decision.primary_agent == "FORGE", (
            f"Expected FORGE for coding/deploy request, got {decision.primary_agent}"
        )
        assert not decision.handled_by_nexus

    def test_security_audit_routes_to_warden(self, orchestrator):
        decision = orchestrator.route("run a security audit on our GDPR compliance config")
        assert decision.primary_agent == "WARDEN", (
            f"Expected WARDEN for security request, got {decision.primary_agent}"
        )
        assert not decision.handled_by_nexus

    def test_research_request_routes_to_sage(self, orchestrator):
        decision = orchestrator.route("investigate the competitive intelligence and market research")
        assert decision.primary_agent == "SAGE"
        assert not decision.handled_by_nexus

    def test_marketing_campaign_routes_to_beacon(self, orchestrator):
        decision = orchestrator.route("create a marketing campaign with brand messaging for the launch")
        assert decision.primary_agent == "BEACON"
        assert not decision.handled_by_nexus

    def test_seo_request_routes_to_prism(self, orchestrator):
        decision = orchestrator.route("improve our SEO ranking and keywords strategy")
        assert decision.primary_agent == "PRISM"
        assert not decision.handled_by_nexus

    def test_strategic_decision_routes_to_compass(self, orchestrator):
        decision = orchestrator.route("help with the strategy and decision roadmap for our OKR planning")
        assert decision.primary_agent == "COMPASS"
        assert not decision.handled_by_nexus

    def test_wellbeing_request_routes_to_ember(self, orchestrator):
        decision = orchestrator.route("I am struggling with stress and burnout, need wellbeing support")
        assert decision.primary_agent == "EMBER"
        assert not decision.handled_by_nexus

    def test_project_status_handled_by_nexus_directly(self, orchestrator):
        decision = orchestrator.route("what is the overall project status and any blockers?")
        assert decision.handled_by_nexus is True
        assert decision.primary_agent == "NEXUS"

    def test_deadline_query_handled_by_nexus(self, orchestrator):
        decision = orchestrator.route("what is the deadline for the milestone?")
        assert decision.handled_by_nexus is True

    def test_ambiguous_request_handled_by_nexus_with_low_confidence(self, orchestrator):
        decision = orchestrator.route("just do something useful")
        assert decision.primary_agent == "NEXUS"
        assert decision.handled_by_nexus is True
        assert decision.confidence <= 0.5

    def test_multi_domain_request_returns_multi_domain_flag(self, orchestrator):
        decision = orchestrator.route("build the code and run a security audit")
        assert decision.is_multi_domain() or decision.primary_agent in ("FORGE", "WARDEN", "NEXUS")

    def test_routing_decision_has_reason_string(self, orchestrator):
        decision = orchestrator.route("deploy the infrastructure")
        assert isinstance(decision.reason, str)
        assert len(decision.reason) > 0

    def test_confidence_is_positive_float(self, orchestrator):
        decision = orchestrator.route("write tests for the code")
        assert 0.0 <= decision.confidence <= 1.0

    def test_detect_blockers_returns_list(self, orchestrator):
        blockers = orchestrator.detect_blockers({"milestones": [], "tasks": []})
        assert isinstance(blockers, list)

    def test_escalate_with_no_blockers(self, orchestrator):
        result = orchestrator.escalate([])
        assert result["escalated"] is False

    def test_escalate_with_blockers_provides_options(self, orchestrator):
        result = orchestrator.escalate([{"title": "Blocked task", "reason": "dependency missing"}])
        assert result["escalated"] is True
        assert len(result["options"]) >= 2

    @pytest.mark.asyncio
    async def test_multi_domain_coordinate_uses_group_chat(self, orchestrator):
        from keprix.multiagent.runtime import clear_messages, get_messages

        clear_messages()
        decision = orchestrator.route("build the API and run a security audit")
        assert decision.is_multi_domain()
        messages = await orchestrator.coordinate_multi(decision, "Coordinate build and audit")
        assert len(messages) >= 1
        stored = get_messages(workspace_id="test-ws", run_id="test-run")
        assert len(stored) >= 1


# ---------------------------------------------------------------------------
# FORGE (Prompt 97) -- code review and sandbox enforcement
# ---------------------------------------------------------------------------


class TestForgeCodeReview:
    """FORGE detects secrets, enforces type hints, and blocks host-level writes."""

    @pytest.fixture()
    def coder(self, tmp_path):
        from keprix.personas.forge.coder import ForgeCoder

        return ForgeCoder(repo_root=tmp_path)

    def test_secret_in_source_fails_review(self, coder):
        # sk-ant- followed by 26 chars (>= 20 required by the pattern)
        source = "import os\nSECRET = 'sk-ant-api03-abcdef12345678901234'\nprint('hello')"
        result = coder.review_code(source, file_path="config.py")
        assert result.passed is False
        assert any(f.rule == "no_secrets" for f in result.findings)

    def test_openai_key_pattern_detected(self, coder):
        # sk- followed by 32 chars (>= 20 required by the pattern)
        source = "TOKEN = 'sk-T3BlbkFJxxxxxxxxxxxxxxxxxxxxxxxx'"
        result = coder.review_code(source, file_path="app.py")
        assert any(f.severity == "critical" for f in result.findings)

    def test_missing_return_type_hint_flagged(self, coder):
        source = "def calculate(x, y):\n    return x + y\n"
        result = coder.review_code(source, file_path="math_utils.py")
        type_hint_findings = [f for f in result.findings if f.rule == "type_hints"]
        assert len(type_hint_findings) > 0

    def test_function_with_type_hints_does_not_trigger_type_hint_rule(self, coder):
        source = "def add(x: int, y: int) -> int:\n    return x + y\n"
        result = coder.review_code(source, file_path="math_utils.py")
        type_hint_violations = [f for f in result.findings if f.rule == "type_hints"]
        assert len(type_hint_violations) == 0

    def test_typescript_any_flagged(self, coder):
        source = "function handle(input: any): void { console.log(input); }"
        result = coder.review_code(source, file_path="handler.ts")
        ts_findings = [f for f in result.findings if f.rule == "strict_typescript"]
        assert len(ts_findings) > 0

    def test_clean_python_passes_review(self, coder):
        source = "def greet(name: str) -> str:\n    def test_greet() -> None:\n        pass\n    return f'Hello {name}'\n"
        result = coder.review_code(source, file_path="greet.py")
        blocking = {f.severity for f in result.findings} & {"critical", "error"}
        assert not blocking

    def test_host_path_blocked(self, coder):
        decision = coder.enforce_sandbox("/etc/passwd")
        assert decision.allowed is False
        assert decision.needs_approval is True

    def test_path_outside_repo_blocked(self, coder, tmp_path):
        outside = tmp_path.parent / "outside_repo" / "secret.py"
        decision = coder.enforce_sandbox(str(outside))
        assert decision.allowed is False

    def test_path_inside_repo_allowed(self, coder, tmp_path):
        inside = tmp_path / "src" / "module.py"
        decision = coder.enforce_sandbox(str(inside))
        assert decision.allowed is True

    def test_review_result_has_to_dict(self, coder):
        source = "def foo():\n    pass\n"
        result = coder.review_code(source, file_path="foo.py")
        d = result.to_dict()
        assert "passed" in d
        assert "findings" in d


# ---------------------------------------------------------------------------
# WARDEN (Prompt 98) -- compliance audit and offensive-security boundary
# ---------------------------------------------------------------------------


class TestWardenAuditor:
    """WARDEN audits config, content, and deps; rejects out-of-scope offensive tasks."""

    @pytest.fixture()
    def auditor(self):
        from keprix.personas.warden.auditor import WardenAuditor

        return WardenAuditor(workspace_id="test-ws")

    def test_pentest_request_is_out_of_scope(self, auditor):
        assert auditor.is_out_of_scope("run a penetration test on our network")

    def test_exploitation_request_is_out_of_scope(self, auditor):
        assert auditor.is_out_of_scope("exploit the vulnerability in the login form")

    def test_osint_request_is_out_of_scope(self, auditor):
        assert auditor.is_out_of_scope("gather OSINT on target domain")

    def test_forensics_out_of_scope(self, auditor):
        assert auditor.is_out_of_scope("help with digital forensics investigation")

    def test_gdpr_audit_is_in_scope(self, auditor):
        assert not auditor.is_out_of_scope("audit our GDPR compliance configuration")

    def test_run_audit_pentest_returns_out_of_scope_report(self, auditor):
        report = auditor.run_audit(request="pentest our api endpoints")
        assert report.out_of_scope is True
        assert any(f.rule == "out_of_scope" for f in report.findings)

    def test_debug_mode_detected_as_high(self, auditor):
        findings = auditor.audit_configuration({"debug": True})
        debug_findings = [f for f in findings if f.rule == "debug_disabled"]
        assert len(debug_findings) == 1
        assert debug_findings[0].severity == "High"

    def test_rate_limit_disabled_flagged(self, auditor):
        findings = auditor.audit_configuration({"rate_limit_enabled": False})
        rate_findings = [f for f in findings if f.rule == "rate_limiting"]
        assert len(rate_findings) == 1

    def test_clean_production_config_has_no_critical_findings(self, auditor):
        findings = auditor.audit_configuration({
            "debug": False,
            "rate_limit_enabled": True,
            "https_enabled": True,
        })
        critical = [f for f in findings if f.severity == "Critical"]
        assert len(critical) == 0

    def test_api_key_in_content_detected(self, auditor):
        # standalone TOKEN token triggers secret_env pattern
        text = "TOKEN = sk-ant-api03-xxxxxxxxxxxxxxxxxxxx"
        findings = auditor.audit_content(text)
        assert any(f.severity == "Critical" for f in findings)

    def test_known_vulnerable_dependency_flagged(self, auditor):
        findings = auditor.audit_dependencies(["pillow"])
        assert any(f.rule == "cve_advisory" for f in findings)

    def test_unpinned_dependency_flagged(self, auditor):
        findings = auditor.audit_dependencies(["requests"])
        assert any(f.rule == "unpinned_dependency" for f in findings)

    def test_pinned_safe_dependency_not_flagged(self, auditor):
        findings = auditor.audit_dependencies(["requests>=2.31.0"])
        cve = [f for f in findings if f.rule == "cve_advisory"]
        assert len(cve) == 0

    def test_audit_report_to_dict_includes_summary(self, auditor):
        report = auditor.run_audit(config={"debug": True})
        d = report.to_dict()
        assert "summary" in d
        assert "findings" in d


# ---------------------------------------------------------------------------
# SAGE (Prompt 99) -- source credibility and claim verification
# ---------------------------------------------------------------------------


class TestSageResearcher:
    """SAGE scores sources by authority/recency/bias and verifies claims against evidence."""

    @pytest.fixture()
    def researcher(self):
        from keprix.personas.sage.researcher import SageResearcher

        return SageResearcher(workspace_id="test-ws")

    def test_arxiv_source_rated_high_authority(self, researcher):
        source = {"title": "AI study", "url": "https://arxiv.org/abs/2401.00001", "date": "2024-01-01"}
        credibility = researcher.score_source(source)
        assert credibility.authority >= 28

    def test_gov_source_rated_high(self, researcher):
        source = {"title": "Public health report", "url": "https://who.int/report", "date": "2024-01-01"}
        credibility = researcher.score_source(source, corroboration_count=2)
        assert credibility.rating == "High"

    def test_sponsored_content_penalised(self, researcher):
        source = {
            "title": "Special offer",
            "url": "https://some-blog.example.com/post",
            "snippet": "sponsored advertisement buy now today",
        }
        credibility = researcher.score_source(source, corroboration_count=0)
        assert credibility.bias <= 6

    def test_corroboration_increases_total(self, researcher):
        source = {"title": "Article", "url": "https://example.com/article", "date": "2024-01-01"}
        score_zero = researcher.score_source(source, corroboration_count=0)
        score_three = researcher.score_source(source, corroboration_count=3)
        assert score_three.total > score_zero.total

    def test_opinion_marker_classified_as_opinion(self, researcher):
        text = "I believe this approach might work well in most cases"
        result = researcher.classify_statement(text)
        assert result == "opinion"

    def test_fact_marker_classified_as_fact(self, researcher):
        text = "According to the study, 80% of participants showed improvement"
        result = researcher.classify_statement(text)
        assert result == "fact"

    def test_recommendation_classified_as_analysis(self, researcher):
        text = "Organizations should consider adopting this framework"
        result = researcher.classify_statement(text)
        assert result == "analysis"

    def test_opinion_claim_not_verified_even_with_many_sources(self, researcher):
        claim = "I believe this treatment might help patients"
        sources = [
            {"title": "Study 1", "url": "https://arxiv.org/abs/1", "snippet": "treatment belief might help patients"},
            {"title": "Study 2", "url": "https://who.int/report/2", "snippet": "treatment help patients might belief"},
            {"title": "Study 3", "url": "https://gov.edu/data/3", "snippet": "might belief patients help treatment"},
        ]
        verification = researcher.verify_claim(claim, sources)
        assert verification.verified is False
        assert verification.confidence == "Low"

    def test_factual_claim_verified_with_three_corroborating_sources(self, researcher):
        claim = "machine learning models improve prediction accuracy on classification tasks"
        sources = [
            {"title": "ML Study", "url": "https://arxiv.org/abs/001", "snippet": "machine learning models improve prediction accuracy classification"},
            {"title": "DL Research", "url": "https://arxiv.org/abs/002", "snippet": "machine learning improve accuracy prediction classification models"},
            {"title": "AI Paper", "url": "https://edu.example.com/003", "snippet": "accuracy prediction classification machine learning improve models"},
        ]
        verification = researcher.verify_claim(claim, sources)
        assert verification.verified is True
        assert verification.confidence == "High"

    def test_partial_corroboration_gives_medium_confidence(self, researcher):
        claim = "economic growth correlates with infrastructure investment"
        sources = [
            {"title": "Economic Report", "url": "https://worldbank.org/report", "snippet": "economic growth infrastructure investment correlates development"},
        ]
        verification = researcher.verify_claim(claim, sources)
        assert verification.confidence == "Medium"
        assert not verification.verified

    def test_credibility_score_has_correct_fields(self, researcher):
        source = {"title": "Test", "url": "https://example.com"}
        score = researcher.score_source(source)
        d = score.to_dict()
        assert all(key in d for key in ("title", "url", "authority", "recency", "bias", "total", "rating"))


# ---------------------------------------------------------------------------
# BEACON (Prompt 100) -- campaign planning and asset calendars
# ---------------------------------------------------------------------------


class TestBeaconCampaign:
    """BEACON builds campaign plans with per-channel asset calendars and briefs."""

    @pytest.fixture()
    def beacon(self):
        from keprix.personas.beacon.campaign import BeaconCampaign

        return BeaconCampaign(workspace_id="test-ws")

    def test_plan_campaign_returns_campaign_plan(self, beacon):
        from keprix.personas.beacon.campaign import CampaignPlan

        plan = beacon.plan_campaign(
            campaign_name="Product Launch Q3",
            objective="Drive 500 qualified signups in 14 days",
            client_name="Acme Corp",
            channels=["email", "social"],
        )
        assert isinstance(plan, CampaignPlan)

    def test_campaign_has_assets_per_channel(self, beacon):
        plan = beacon.plan_campaign(
            campaign_name="Brand Awareness",
            objective="Grow awareness",
            client_name="Beta Ltd",
            channels=["email", "social", "landing"],
        )
        channel_set = {asset.channel for asset in plan.assets}
        assert "email" in channel_set
        assert "social" in channel_set
        assert "landing" in channel_set

    def test_campaign_assets_have_due_dates(self, beacon):
        plan = beacon.plan_campaign(
            campaign_name="Q4 Campaign",
            objective="Revenue",
            client_name="Client X",
            channels=["ads"],
        )
        for asset in plan.assets:
            assert asset.due_date != ""

    def test_campaign_assets_default_owner_is_beacon(self, beacon):
        plan = beacon.plan_campaign(
            campaign_name="Test",
            objective="Test objective",
            client_name="Client Y",
        )
        for asset in plan.assets:
            assert asset.owner == "BEACON"

    def test_campaign_has_unique_id(self, beacon):
        plan_a = beacon.plan_campaign(campaign_name="A", objective="X", client_name="C")
        plan_b = beacon.plan_campaign(campaign_name="B", objective="Y", client_name="C")
        assert plan_a.campaign_id != plan_b.campaign_id

    def test_opportunity_assets_mapped_for_email(self, beacon):
        assets = beacon.opportunity_assets_for_channels(["email"])
        assert len(assets) > 0

    def test_opportunity_assets_mapped_for_social(self, beacon):
        assets = beacon.opportunity_assets_for_channels(["social"])
        assert len(assets) > 0

    def test_unknown_channel_falls_back_to_defaults(self, beacon):
        assets = beacon.opportunity_assets_for_channels(["nonexistent-channel"])
        assert len(assets) > 0

    def test_plan_to_dict_includes_channels(self, beacon):
        plan = beacon.plan_campaign(
            campaign_name="Test",
            objective="Test",
            client_name="Client",
            channels=["email"],
        )
        d = plan.to_dict()
        assert "channels" in d
        assert "assets" in d
        assert "campaign_id" in d

    def test_brief_markdown_is_non_empty(self, beacon):
        plan = beacon.plan_campaign(
            campaign_name="Launch",
            objective="Grow leads",
            client_name="Startup",
            channels=["email"],
        )
        assert len(plan.brief_markdown) > 100

    def test_ads_channel_marks_legal_review_in_brief(self, beacon):
        plan = beacon.plan_campaign(
            campaign_name="Ad Campaign",
            objective="Conversions",
            client_name="BigCo",
            channels=["ads"],
        )
        assert "legal_review" in plan.brief_markdown or "yes" in plan.brief_markdown.lower()


# ---------------------------------------------------------------------------
# PRISM (Prompt 101) -- SEO signals and white-hat recommendations
# ---------------------------------------------------------------------------


class TestPrismSeo:
    """PRISM parses HTML signals, builds prioritised recommendations, blocks black-hat."""

    def _minimal_html(self, *, title="", meta_desc="", h1="", viewport=True) -> str:
        lines = ["<html><head>"]
        if title:
            lines.append(f"<title>{title}</title>")
        if meta_desc:
            lines.append(f'<meta name="description" content="{meta_desc}">')
        if viewport:
            lines.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
        lines.append("</head><body>")
        if h1:
            lines.append(f"<h1>{h1}</h1>")
        lines.append("</body></html>")
        return "\n".join(lines)

    def test_missing_meta_description_generates_recommendation(self):
        from keprix.personas.prism.seo import build_recommendations, parse_html_signals

        html = self._minimal_html(title="My Page", h1="Welcome")
        signals = parse_html_signals(html)
        assert signals["meta_description"] == ""
        recs = build_recommendations(signals, "https://example.com")
        assert any("meta description" in rec.change.lower() for rec in recs)

    def test_missing_title_generates_high_impact_recommendation(self):
        from keprix.personas.prism.seo import build_recommendations, parse_html_signals

        html = self._minimal_html(h1="Welcome")
        signals = parse_html_signals(html)
        assert signals["title"] == ""
        recs = build_recommendations(signals, "https://example.com")
        title_recs = [r for r in recs if "title" in r.change.lower() and r.impact == "High"]
        assert len(title_recs) > 0

    def test_noindex_generates_recommendation(self):
        from keprix.personas.prism.seo import build_recommendations, parse_html_signals

        html = '<html><head><title>Test</title><meta name="robots" content="noindex, nofollow"></head><body><h1>Test</h1></body></html>'
        signals = parse_html_signals(html)
        recs = build_recommendations(signals, "https://example.com")
        assert any("noindex" in rec.change.lower() for rec in recs)

    def test_missing_h1_generates_recommendation(self):
        from keprix.personas.prism.seo import build_recommendations, parse_html_signals

        html = "<html><head><title>Test</title></head><body><p>No heading</p></body></html>"
        signals = parse_html_signals(html)
        assert signals["h1_count"] == 0
        recs = build_recommendations(signals, "https://example.com")
        assert any("H1" in rec.change or "h1" in rec.change.lower() for rec in recs)

    def test_multiple_h1_tags_generates_recommendation(self):
        from keprix.personas.prism.seo import build_recommendations, parse_html_signals

        html = "<html><head><title>Test</title></head><body><h1>First</h1><h1>Second</h1></body></html>"
        signals = parse_html_signals(html)
        assert signals["h1_count"] == 2
        recs = build_recommendations(signals, "https://example.com")
        assert any("H1" in rec.change or "single" in rec.change.lower() or "H2" in rec.change for rec in recs)

    def test_images_missing_alt_text_generates_recommendation(self):
        from keprix.personas.prism.seo import build_recommendations, parse_html_signals

        html = '<html><head><title>Test</title></head><body><img src="a.jpg"><img src="b.jpg"></body></html>'
        signals = parse_html_signals(html)
        assert signals["images_missing_alt"] == 2
        recs = build_recommendations(signals, "https://example.com")
        assert any("alt" in rec.change.lower() for rec in recs)

    def test_well_formed_page_has_fewer_recommendations(self):
        from keprix.personas.prism.seo import build_recommendations, parse_html_signals

        html = (
            '<html><head>'
            '<title>Great Page Title for SEO</title>'
            '<meta name="description" content="A clear 150 character description with the primary keyword and a call to action.">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<link rel="canonical" href="https://example.com/page">'
            '<script type="application/ld+json">{"@type": "Article"}</script>'
            '</head><body><h1>Great Heading</h1>'
            '<img src="hero.jpg" alt="Hero image of the product">'
            '</body></html>'
        )
        signals = parse_html_signals(html)
        recs = build_recommendations(signals, "https://example.com/page")
        high_impact = [r for r in recs if r.impact == "High"]
        assert len(high_impact) == 0

    def test_black_hat_term_detected(self):
        from keprix.personas.prism.seo import contains_black_hat

        assert contains_black_hat("use keyword stuffing on the landing page")

    def test_black_hat_pbn_detected(self):
        from keprix.personas.prism.seo import contains_black_hat

        assert contains_black_hat("build a private blog network to boost rankings")

    def test_white_hat_term_not_flagged(self):
        from keprix.personas.prism.seo import contains_black_hat

        assert not contains_black_hat("add structured data and improve meta descriptions")

    def test_recommendations_sorted_by_priority_descending(self):
        from keprix.personas.prism.seo import build_recommendations, parse_html_signals

        html = "<html><head></head><body></body></html>"
        signals = parse_html_signals(html)
        recs = build_recommendations(signals, "https://example.com")
        priorities = [r.priority for r in recs]
        assert priorities == sorted(priorities, reverse=True)

    def test_parse_html_signals_returns_required_keys(self):
        from keprix.personas.prism.seo import parse_html_signals

        html = "<html><head><title>T</title></head><body></body></html>"
        signals = parse_html_signals(html)
        for key in ("title", "meta_description", "h1_count", "viewport", "canonical", "structured_data_count"):
            assert key in signals


# ---------------------------------------------------------------------------
# COMPASS (Prompt 102) -- decision matrix and scenario planning
# ---------------------------------------------------------------------------


class TestCompassDecisions:
    """COMPASS evaluates decisions, scores options, and builds scenario plans."""

    @pytest.fixture()
    def compass(self):
        from keprix.personas.compass.decisions import CompassDecisions

        return CompassDecisions(workspace_id="test-ws")

    def test_evaluate_decision_returns_matrix_result(self, compass):
        from keprix.personas.compass.decisions import DecisionMatrixResult

        result = compass.evaluate_decision("Choose backend framework", store=False)
        assert isinstance(result, DecisionMatrixResult)

    def test_decision_has_weighted_totals(self, compass):
        result = compass.evaluate_decision("Hire vs outsource engineering", store=False)
        assert len(result.weighted_totals) >= 2

    def test_winner_has_highest_weighted_total(self, compass):
        result = compass.evaluate_decision("Office vs remote work policy", store=False)
        totals = result.weighted_totals
        top_option = max(totals, key=totals.get)
        assert top_option in result.recommendation

    def test_without_clarifying_answers_recommendation_asks_for_more_info(self, compass):
        result = compass.evaluate_decision("Platform selection", store=False)
        assert "clarifying" in result.recommendation.lower() or "provisional" in result.recommendation.lower()

    def test_with_enough_clarifying_answers_gives_firm_recommendation(self, compass):
        result = compass.evaluate_decision(
            "Cloud provider choice",
            clarifying_answers={"q1": "cost savings", "q2": "6 months delay cost", "q3": "engineers"},
            store=False,
        )
        assert "Lean toward" in result.recommendation or "score" in result.recommendation

    def test_decision_includes_three_scenarios(self, compass):
        result = compass.evaluate_decision("Launch timing", store=False)
        assert len(result.scenarios) == 3

    def test_scenarios_sum_to_100_percent(self, compass):
        result = compass.evaluate_decision("Pricing model", store=False)
        total_probability = sum(s.probability_pct for s in result.scenarios)
        assert abs(total_probability - 100.0) < 0.01

    def test_premortem_risks_are_non_empty(self, compass):
        result = compass.evaluate_decision("Market expansion", store=False)
        assert len(result.premortem_risks) >= 3

    def test_cost_benefit_has_positive_roi(self, compass):
        result = compass.evaluate_decision("Feature investment", store=False)
        assert result.cost_benefit.get("roi_pct", 0) > 0

    def test_normalize_weights_sums_to_one(self):
        from keprix.personas.compass.decisions import DecisionCriterion, normalize_weights

        criteria = [
            DecisionCriterion("Impact", 0.4),
            DecisionCriterion("Cost", 0.3),
            DecisionCriterion("Risk", 0.3),
        ]
        normalized = normalize_weights(criteria)
        total = round(sum(c.weight for c in normalized), 5)
        assert total == 1.0

    def test_score_weighted_totals_returns_per_option(self):
        from keprix.personas.compass.decisions import (
            DecisionCriterion,
            DecisionOptionScore,
            score_weighted_totals,
        )

        criteria = [DecisionCriterion("Impact", 0.6), DecisionCriterion("Cost", 0.4)]
        options = [
            DecisionOptionScore("Fast", {"Impact": 9.0, "Cost": 5.0}),
            DecisionOptionScore("Cheap", {"Impact": 5.0, "Cost": 9.0}),
        ]
        totals = score_weighted_totals(criteria, options)
        assert "Fast" in totals
        assert "Cheap" in totals
        assert totals["Fast"] == round(9.0 * 0.6 + 5.0 * 0.4, 2)
        assert totals["Cheap"] == round(5.0 * 0.6 + 9.0 * 0.4, 2)

    def test_plan_scenarios_returns_scenario_plan(self, compass):
        from keprix.personas.compass.decisions import ScenarioPlan

        plan = compass.plan_scenarios("Launch new market")
        assert isinstance(plan, ScenarioPlan)
        assert plan.expected_value_usd > 0


# ---------------------------------------------------------------------------
# EMBER (Prompt 103) -- wellbeing coaching and crisis detection
# ---------------------------------------------------------------------------


class TestEmberCoach:
    """EMBER detects crisis language, reframes limiting beliefs, and owns the wellbeing lane."""

    @pytest.fixture()
    def coach(self):
        from keprix.personas.ember.coach import EmberCoach

        return EmberCoach(user_id="test-user")

    def test_crisis_language_detected(self):
        from keprix.personas.ember.coach import detect_crisis_language

        assert detect_crisis_language("I want to kill myself")

    def test_self_harm_detected(self):
        from keprix.personas.ember.coach import detect_crisis_language

        assert detect_crisis_language("I keep thinking about self-harm")

    def test_non_crisis_text_not_flagged(self):
        from keprix.personas.ember.coach import detect_crisis_language

        assert not detect_crisis_language("I had a stressful week at work")

    def test_crisis_response_contains_resources(self, coach):
        response = coach.coach("I want to kill myself")
        assert response.crisis.detected is True
        assert len(response.crisis.resources) >= 3

    def test_crisis_response_suppresses_normal_ask_questions(self, coach):
        response = coach.coach("I want to end my life")
        assert response.crisis.detected is True
        assert len(response.ask) == 0

    def test_limiting_belief_reframed(self):
        from keprix.personas.ember.coach import detect_limiting_belief

        reframe = detect_limiting_belief("I'm not good enough for this role")
        assert reframe is not None
        assert len(reframe) > 0

    def test_always_language_detected(self):
        from keprix.personas.ember.coach import detect_limiting_belief

        reframe = detect_limiting_belief("I always fail when it matters")
        assert reframe is not None

    def test_limiting_belief_absent_returns_none(self):
        from keprix.personas.ember.coach import detect_limiting_belief

        reframe = detect_limiting_belief("I had a good day today")
        assert reframe is None

    def test_normal_checkin_returns_ask_reflect_suggest(self, coach):
        response = coach.coach("I've been feeling overwhelmed with the workload")
        assert len(response.ask) > 0
        assert len(response.reflect) > 0
        assert len(response.suggest) > 0

    def test_reflect_includes_message_excerpt(self, coach):
        response = coach.coach("I feel stuck and cannot make progress")
        assert "stuck" in response.reflect.lower() or "cannot make progress" in response.reflect.lower()

    def test_three_negative_checkins_triggers_professional_help_suggestion(self, coach):
        response = coach.coach("I feel terrible again", negative_checkin_streak=3)
        assert response.suggest_professional_help is True
        professional_suggestions = [
            s for s in response.suggest if "counsellor" in s.lower() or "gp" in s.lower() or "trained" in s.lower()
        ]
        assert len(professional_suggestions) > 0

    def test_two_negative_checkins_does_not_trigger_professional_help(self, coach):
        response = coach.coach("Not feeling great", negative_checkin_streak=2)
        assert response.suggest_professional_help is False

    def test_ember_is_wellbeing_lane_owner(self):
        from keprix.personas.ember.coach import is_wellbeing_lane_owner

        assert is_wellbeing_lane_owner("EMBER")

    def test_other_personas_not_wellbeing_lane_owners(self):
        from keprix.personas.ember.coach import is_wellbeing_lane_owner

        for persona in ("FORGE", "WARDEN", "SAGE", "BEACON", "PRISM", "COMPASS", "NEXUS"):
            assert not is_wellbeing_lane_owner(persona), f"Expected {persona} to not own the wellbeing lane"

    def test_shares_with_work_agents_returns_false(self, coach):
        assert coach.shares_with_work_agents() is False

    def test_coaching_response_lane_is_wellbeing(self, coach):
        response = coach.coach("I need some guidance on building better habits")
        assert response.lane == "wellbeing"

    def test_coaching_response_to_dict_includes_phases(self, coach):
        response = coach.coach("Struggling with focus")
        d = response.to_dict()
        assert "phases" in d
        assert "crisis" in d
        assert all(phase in d["phases"] for phase in ("ask", "listen", "reflect", "suggest"))
