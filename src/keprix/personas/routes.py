"""HTTP routes for agent personas (Prompt 96)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from keprix.multiagent.runtime import clear_messages, get_messages
from keprix.personas.forge.architect import ArchitectureDecision, ForgeArchitect
from keprix.personas.forge.coder import FORGE_SANDBOX_MODE, ForgeCoder, ForgeSandboxConfig
from keprix.personas.forge.deploy import ForgeDeployPipeline
from keprix.personas.warden.auditor import WardenAuditor
from keprix.personas.warden.hardener import WardenHardener
from keprix.personas.warden.privacy import WardenPrivacy
from keprix.personas.sage.briefer import SageBriefer
from keprix.personas.sage.intel import SageIntel
from keprix.personas.sage.researcher import SageResearcher
from keprix.personas.beacon.campaign import BeaconCampaign
from keprix.personas.beacon.copywriter import BeaconCopywriter, BrandVoice
from keprix.personas.beacon.delivery import BeaconDelivery
from keprix.personas.prism.analytics import PrismAnalytics
from keprix.personas.prism.keywords import PrismKeywords
from keprix.personas.prism.seo import PrismSeo
from keprix.personas.prism.social import PrismSocial
from keprix.personas.compass.analyst import CompassAnalyst
from keprix.personas.compass.decisions import CompassDecisions
from keprix.personas.compass.strategist import CompassStrategist
from keprix.personas.ember.checkin import EmberCheckin
from keprix.personas.ember.coach import EmberCoach
from keprix.personas.ember.habits import EmberHabits
from keprix.personas.codex.drafter import CodexDrafter
from keprix.personas.codex.researcher import CodexResearcher
from keprix.personas.codex.reviewer import CodexReviewer
from keprix.extensions.scout.persona.policy_bridge import GovernancePolicyBridge
from keprix.personas.echo.knowledge import BusinessProfile, EchoKnowledge
from keprix.personas.echo.receptionist import EchoReceptionist
from keprix.personas.echo.scheduler import EchoScheduler
from keprix.personas.nexus.orchestrator import NexusOrchestrator
from keprix.personas.nexus.project_tracker import ProjectState
from keprix.personas.improvement_hook import record_routing_outcome
from keprix.personas.registry import get_persona_registry
from keprix.mutation.persona_mutation_store import merge_persona_dict

router = APIRouter(prefix="/api/personas", tags=["personas"])


class RouteBody(BaseModel):
    message: str = Field(..., min_length=1)
    workspace_id: str = Field(default="default")
    run_id: str = Field(default="run")


class DelegateBody(RouteBody):
    coordinate_multi: bool = False


class StatusReportBody(BaseModel):
    workspace_id: str = Field(default="default")
    project_name: str = Field(default="Untitled Project")
    state: dict[str, Any] = Field(default_factory=dict)


class ForgeReviewBody(BaseModel):
    source: str = Field(..., min_length=1)
    file_path: str = Field(default="snippet.py")


class ForgeGenerateBody(BaseModel):
    task: str = Field(..., min_length=1)
    workspace_id: str = Field(default="default")
    code: str | None = None


class ForgeAdrBody(BaseModel):
    title: str = Field(..., min_length=1)
    context: str = Field(..., min_length=1)
    decision: str = Field(..., min_length=1)
    workspace_id: str = Field(default="default")
    status: str = Field(default="proposed")
    positive_consequences: str = Field(default="")
    negative_consequences: str = Field(default="")
    alternatives: str = Field(default="")
    implementation_notes: str = Field(default="")


class ForgeDeployBody(BaseModel):
    project_root: str = Field(..., min_length=1)
    target: str = Field(default="local")
    app_name: str | None = None


class WardenAuditBody(BaseModel):
    workspace_id: str = Field(default="default")
    request: str = Field(default="")
    config: dict[str, Any] = Field(default_factory=dict)
    content_samples: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    encryption_key: str = Field(default="")


class WardenHardenBody(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)
    recommendation_id: str = Field(default="")
    approved: bool = Field(default=False)


class WardenPrivacyBody(BaseModel):
    text: str = Field(default="")
    files: dict[str, str] = Field(default_factory=dict)


class SageResearchBody(BaseModel):
    query: str = Field(..., min_length=1)
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    claims: list[str] = Field(default_factory=list)
    index_to_rag: bool = Field(default=True)


class SageBriefBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    query: str = Field(..., min_length=1)
    sources: list[dict[str, Any]] = Field(default_factory=list)


class SageIntelBody(BaseModel):
    workspace_id: str = Field(default="default")
    topic: str = Field(..., min_length=1)
    competitors: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)


class BeaconCopyBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    client_id: str = Field(default="default")
    format_type: str = Field(default="landing_page")
    brief: dict[str, str] = Field(default_factory=dict)
    store: bool = Field(default=True)


class BeaconBrandVoiceBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    client_id: str = Field(default="default")
    voice: dict[str, Any] = Field(default_factory=dict)


class BeaconCampaignBody(BaseModel):
    workspace_id: str = Field(default="default")
    campaign_name: str = Field(..., min_length=1)
    objective: str = Field(..., min_length=1)
    client_name: str = Field(default="default")
    channels: list[str] = Field(default_factory=list)
    duration_days: int = Field(default=14)
    audience: str = Field(default="")
    key_message: str = Field(default="")


class BeaconDeliverBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    client_id: str = Field(default="default")
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    output_format: str = Field(default="pdf")
    target_languages: list[str] = Field(default_factory=list)
    store: bool = Field(default=True)


class PrismAuditBody(BaseModel):
    url: str = Field(..., min_length=1)
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    html_content: str | None = None
    use_browser: bool = Field(default=True)
    index_to_rag: bool = Field(default=True)


class PrismBriefBody(BaseModel):
    workspace_id: str = Field(default="default")
    primary_keyword: str = Field(..., min_length=1)
    intent: str = Field(default="informational")
    target_url: str = Field(default="/blog")
    search_volume: int = Field(default=500)
    difficulty: int = Field(default=35)
    audience: str = Field(default="")
    competitor_gap: str = Field(default="")


class PrismKeywordsBody(BaseModel):
    workspace_id: str = Field(default="default")
    seed: str = Field(..., min_length=1)
    limit: int = Field(default=12)


class PrismGapBody(BaseModel):
    workspace_id: str = Field(default="default")
    seed: str = Field(..., min_length=1)
    our_keywords: list[str] = Field(default_factory=list)
    competitor_keywords: list[str] = Field(default_factory=list)
    limit: int = Field(default=10)


class PrismSocialBody(BaseModel):
    workspace_id: str = Field(default="default")
    topic: str = Field(..., min_length=1)
    platforms: list[str] = Field(default_factory=list)
    duration_days: int = Field(default=14)


class PrismAnalyticsBody(BaseModel):
    workspace_id: str = Field(default="default")
    weeks: int = Field(default=8)
    keyword_rankings: dict[str, list[int]] = Field(default_factory=dict)
    traffic_by_week: list[int] = Field(default_factory=list)
    conversions_by_week: list[int] = Field(default_factory=list)


class CompassClarifyBody(BaseModel):
    workspace_id: str = Field(default="default")
    topic: str = Field(..., min_length=1)
    extra_context: str = Field(default="")


class CompassStrategyBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    topic: str = Field(..., min_length=1)
    framework: str = Field(default="swot")
    answers: dict[str, str] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    store: bool = Field(default=True)


class CompassAnalyzeBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    market: str = Field(..., min_length=1)
    competitor_names: list[str] = Field(default_factory=list)
    opportunity_artifacts: dict[str, str] = Field(default_factory=dict)
    geography: str = Field(default="global")
    use_research: bool = Field(default=False)
    store: bool = Field(default=True)


class CompassDecideBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    decision_title: str = Field(..., min_length=1)
    clarifying_answers: dict[str, str] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    base_impact_usd: int = Field(default=100_000)
    store: bool = Field(default=True)


class CompassScenariosBody(BaseModel):
    workspace_id: str = Field(default="default")
    decision_title: str = Field(..., min_length=1)
    base_impact_usd: int = Field(default=100_000)
    assumptions: list[str] = Field(default_factory=list)


class EmberCoachBody(BaseModel):
    user_id: str = Field(default="default")
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    context: str = Field(default="")
    negative_checkin_streak: int = Field(default=0)
    store: bool = Field(default=True)


class EmberHabitCreateBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    name: str = Field(..., min_length=1)
    frequency: str = Field(default="daily")
    motivation: str = Field(default="")
    tiny_start: str = Field(default="")
    cue: str = Field(default="")
    reward: str = Field(default="")


class EmberHabitCompleteBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    habit_id: str = Field(..., min_length=1)


class EmberCheckinBody(BaseModel):
    user_id: str = Field(default="default")
    energy: int = Field(..., ge=1, le=5)
    stress: int = Field(..., ge=1, le=5)
    focus: int = Field(..., ge=1, le=5)
    sleep: int = Field(..., ge=1, le=5)
    mood: int = Field(..., ge=1, le=5)
    notes: str = Field(default="")


class EmberCheckinScheduleBody(BaseModel):
    user_id: str = Field(default="default")
    frequency: str = Field(default="daily")
    topics: list[str] = Field(default_factory=list)


class CodexReviewBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    title: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    jurisdiction: str = Field(default="England and Wales (UK)")
    store: bool = Field(default=True)
    index_to_rag: bool = Field(default=True)


class CodexDraftBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    document_type: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    jurisdiction: str = Field(default="England and Wales (UK)")
    parties: dict[str, str] = Field(default_factory=dict)
    store: bool = Field(default=True)


class CodexAskBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    question: str = Field(..., min_length=1)
    jurisdiction: str = Field(default="England and Wales (UK)")


class CodexRegulatoryBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    topic: str = Field(..., min_length=1)
    jurisdiction: str = Field(default="United Kingdom")
    use_research: bool = Field(default=True)
    store: bool = Field(default=True)


class CodexChecklistBody(BaseModel):
    checklist_type: str = Field(..., min_length=1)
    jurisdiction: str = Field(default="England and Wales (UK)")


class GovernanceCheckpointBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    tool_name: str = Field(..., min_length=1)
    persona: str = Field(default="FORGE")


class GovernanceKillBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    level: str = Field(..., min_length=1)
    reason: str = Field(default="Manual kill switch activation")
    propagate_scheduler: bool = Field(default=True)


class GovernanceAuditBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    event_type: str = Field(..., min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class GovernanceEvidenceBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    limit: int = Field(default=25, ge=1, le=200)


class GovernanceConnectorBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    action: str = Field(default="status")


class EchoWebhookBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    payload: dict[str, Any] = Field(default_factory=dict)


class EchoBookBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    call_id: str = Field(..., min_length=1)
    slot_index: int = Field(default=0, ge=0)
    title: str = Field(default="Phone appointment")


class EchoAskBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    question: str = Field(..., min_length=1)
    business_name: str = Field(default="Your Business")
    hours: str = Field(default="Monday to Friday, 9am to 5pm")
    location: str = Field(default="")


class EchoSlotsBody(BaseModel):
    workspace_id: str = Field(default="default")
    user_id: str = Field(default="default")
    days: int = Field(default=5, ge=1, le=30)
    count: int = Field(default=4, ge=1, le=20)


class EchoProfileBody(BaseModel):
    business_name: str = Field(default="Your Business")
    hours: str = Field(default="Monday to Friday, 9am to 5pm")
    location: str = Field(default="")
    services: str = Field(default="")
    pricing_note: str = Field(default="Please speak with our team for a tailored quote.")
    parking_note: str = Field(default="")
    primary_language: str = Field(default="en-GB")


@router.get("")
async def list_personas(workspace_id: str = "default") -> dict[str, Any]:
    registry = get_persona_registry()
    personas = [merge_persona_dict(persona, workspace_id) for persona in registry.list_personas()]
    return {"personas": personas}


@router.get("/{name}")
async def get_persona(name: str, workspace_id: str = "default") -> dict[str, Any]:
    persona = get_persona_registry().get(name)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")
    return merge_persona_dict(persona.to_dict(), workspace_id)


@router.get("/{name}/skill-packs")
async def get_persona_skill_packs(name: str) -> dict[str, Any]:
    persona = get_persona_registry().get(name)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")
    packs = get_persona_registry().load_skill_pack_content(name)
    return {"persona": persona.name, "skill_packs": packs}


@router.post("/nexus/route")
async def nexus_route(body: RouteBody) -> dict[str, Any]:
    orchestrator = NexusOrchestrator(workspace_id=body.workspace_id, run_id=body.run_id)
    decision = orchestrator.route(body.message)
    return {
        "primary_agent": decision.primary_agent,
        "matched_agents": decision.matched_agents,
        "handled_by_nexus": decision.handled_by_nexus,
        "reason": decision.reason,
        "confidence": decision.confidence,
        "is_multi_domain": decision.is_multi_domain(),
    }


@router.post("/nexus/delegate")
async def nexus_delegate(body: DelegateBody) -> dict[str, Any]:
    orchestrator = NexusOrchestrator(workspace_id=body.workspace_id, run_id=body.run_id)
    decision = orchestrator.route(body.message)
    if body.coordinate_multi and decision.is_multi_domain():
        messages = await orchestrator.coordinate_multi(decision, body.message)
    else:
        messages = await orchestrator.delegate(decision, body.message)
    proposals = record_routing_outcome(
        run_id=body.run_id,
        primary_agent=decision.primary_agent,
        matched_agents=decision.matched_agents,
        message_count=len(messages),
        metadata={
            "workspace_id": body.workspace_id,
            "handled_by_nexus": decision.handled_by_nexus,
            "reason": decision.reason,
            "coordinate_multi": body.coordinate_multi,
        },
    )
    return {
        "decision": {
            "primary_agent": decision.primary_agent,
            "matched_agents": decision.matched_agents,
            "handled_by_nexus": decision.handled_by_nexus,
            "reason": decision.reason,
        },
        "messages": [message.to_dict() for message in messages],
        "improvement_proposals": [proposal.to_dict() for proposal in proposals],
    }


@router.post("/nexus/status-report")
async def nexus_status_report(body: StatusReportBody) -> dict[str, Any]:
    state = ProjectState.from_playbook_state(body.state)
    state.workspace_id = body.workspace_id
    state.project_name = body.project_name
    blockers = state.detect_blockers()
    orchestrator = NexusOrchestrator(workspace_id=body.workspace_id, run_id="status")
    escalation = orchestrator.escalate(blockers)
    return {
        "report": state.generate_status_report(),
        "overall_status": state.overall_status(),
        "blockers": blockers,
        "escalation": escalation,
        "playbook_state": state.to_playbook_state(),
    }


@router.get("/nexus/messages")
async def nexus_messages(workspace_id: str | None = None, run_id: str | None = None) -> dict[str, Any]:
    messages = get_messages(workspace_id=workspace_id, run_id=run_id)
    return {"messages": [message.to_dict() for message in messages]}


@router.delete("/nexus/messages")
async def nexus_clear_messages() -> dict[str, bool]:
    clear_messages()
    return {"cleared": True}


@router.post("/forge/review")
async def forge_review(body: ForgeReviewBody) -> dict[str, Any]:
    from pathlib import Path

    coder = ForgeCoder(repo_root=Path.cwd())
    result = coder.review_code(body.source, file_path=body.file_path)
    return result.to_dict()


@router.post("/forge/generate")
async def forge_generate(body: ForgeGenerateBody) -> dict[str, Any]:
    from pathlib import Path

    coder = ForgeCoder(
        repo_root=Path.cwd(),
        sandbox=ForgeSandboxConfig(workspace_id=body.workspace_id),
    )
    result = coder.generate_code(body.task, code=body.code)
    return {
        "ok": result.ok,
        "code": result.code,
        "result": result.result,
        "needs_approval": result.needs_approval,
        "errors": result.errors,
        "sandbox_mode": FORGE_SANDBOX_MODE,
    }


@router.post("/forge/adr")
async def forge_adr(body: ForgeAdrBody) -> dict[str, Any]:
    architect = ForgeArchitect(workspace_id=body.workspace_id)
    decision = ArchitectureDecision(
        title=body.title,
        context=body.context,
        decision=body.decision,
        status=body.status,
        positive_consequences=body.positive_consequences,
        negative_consequences=body.negative_consequences,
        alternatives=body.alternatives,
        implementation_notes=body.implementation_notes,
    )
    return await architect.record_adr(decision)


@router.post("/forge/build")
async def forge_build(body: ForgeDeployBody) -> dict[str, Any]:
    from pathlib import Path

    pipeline = ForgeDeployPipeline(project_root=Path(body.project_root))
    return {
        "targets": pipeline.detect_build_targets(),
        "result": pipeline.run_build().to_dict(),
    }


@router.post("/forge/deploy")
async def forge_deploy(body: ForgeDeployBody) -> dict[str, Any]:
    from pathlib import Path

    pipeline = ForgeDeployPipeline(project_root=Path(body.project_root))
    return pipeline.run_deploy(target=body.target, app_name=body.app_name).to_dict()


@router.post("/warden/audit")
async def warden_audit(body: WardenAuditBody) -> dict[str, Any]:
    auditor = WardenAuditor(workspace_id=body.workspace_id)
    report = auditor.run_audit(
        request=body.request,
        config=body.config or None,
        content_samples=body.content_samples or None,
        requirements=body.requirements or None,
    )
    result: dict[str, Any] = {"report": report.to_dict()}
    if body.encryption_key:
        result["encrypted"] = auditor.encrypt_report(report, encryption_key=body.encryption_key)
    return result


@router.post("/warden/audit/playbook")
async def warden_audit_playbook(body: WardenAuditBody) -> dict[str, Any]:
    auditor = WardenAuditor(workspace_id=body.workspace_id)
    return await auditor.run_audit_playbook(
        {
            "config": body.config,
            "content_samples": body.content_samples,
            "requirements": body.requirements,
        }
    )


@router.post("/warden/harden/assess")
async def warden_harden_assess(body: WardenHardenBody) -> dict[str, Any]:
    hardener = WardenHardener()
    recommendations = hardener.assess(body.config)
    return {"recommendations": [rec.to_dict() for rec in recommendations]}


@router.post("/warden/harden/apply")
async def warden_harden_apply(body: WardenHardenBody) -> dict[str, Any]:
    if not body.recommendation_id:
        raise HTTPException(status_code=400, detail="recommendation_id required")
    hardener = WardenHardener()
    config = dict(body.config)
    return hardener.apply(body.recommendation_id, config, approved=body.approved)


@router.post("/warden/privacy/scan")
async def warden_privacy_scan(body: WardenPrivacyBody) -> dict[str, Any]:
    privacy = WardenPrivacy()
    if body.files:
        result = privacy.scan_files(body.files)
    else:
        result = privacy.scan(body.text)
    return {
        **result.to_dict(),
        "recommendations": privacy.recommend_actions(result),
    }


@router.post("/sage/research")
async def sage_research(body: SageResearchBody) -> dict[str, Any]:
    researcher = SageResearcher(workspace_id=body.workspace_id, user_id=body.user_id)
    result = await researcher.research(
        body.query,
        claims=body.claims or None,
        index_to_rag=body.index_to_rag,
    )
    return result.to_dict()


@router.post("/sage/brief")
async def sage_brief(body: SageBriefBody) -> dict[str, Any]:
    researcher = SageResearcher(workspace_id=body.workspace_id, user_id=body.user_id)
    result = await researcher.research(
        body.query,
        sources=body.sources or None,
        index_to_rag=False,
    )
    briefer = SageBriefer(workspace_id=body.workspace_id)
    brief = await briefer.generate_brief(result)
    return brief.to_dict()


@router.post("/sage/intel/monitor")
async def sage_intel_monitor(body: SageIntelBody) -> dict[str, Any]:
    intel = SageIntel(workspace_id=body.workspace_id)
    if body.sources:
        for row in body.sources:
            intel.add_source(row.get("name", "source"), row.get("url", ""), source_type=row.get("source_type", "site"))
    if body.sources and not body.competitors:
        snippets = body.sources
        report = intel.analyze_signals(topic=body.topic, snippets=snippets, competitors=body.competitors)
    else:
        report = await intel.run_monitoring_cycle(topic=body.topic, competitors=body.competitors)
    return report.to_dict()


@router.post("/beacon/copy")
async def beacon_copy(body: BeaconCopyBody) -> dict[str, Any]:
    writer = BeaconCopywriter(workspace_id=body.workspace_id, user_id=body.user_id)
    result = writer.generate_copy(
        format_type=body.format_type,
        brief=body.brief,
        client_id=body.client_id,
        store=body.store,
    )
    return result.to_dict()


@router.post("/beacon/brand-voice")
async def beacon_save_brand_voice(body: BeaconBrandVoiceBody) -> dict[str, Any]:
    writer = BeaconCopywriter(workspace_id=body.workspace_id, user_id=body.user_id)
    voice = BrandVoice(
        client_name=body.voice.get("client_name", body.client_id),
        voice_summary=body.voice.get("voice_summary", ""),
        formality=body.voice.get("formality", "professional"),
        energy=body.voice.get("energy", "balanced"),
        humor=body.voice.get("humor", "minimal"),
        technical_depth=body.voice.get("technical_depth", "moderate"),
        preferred_terms=list(body.voice.get("preferred_terms", [])),
        banned_terms=list(body.voice.get("banned_terms", [])),
        do_list=list(body.voice.get("do_list", [])),
        dont_list=list(body.voice.get("dont_list", [])),
        example_phrases=list(body.voice.get("example_phrases", [])),
    )
    doc = writer.save_brand_voice(body.client_id, voice)
    return {"brand_voice": voice.to_dict(), "document": doc}


@router.get("/beacon/brand-voice/{client_id}")
async def beacon_get_brand_voice(
    client_id: str,
    workspace_id: str = "default",
    user_id: str = "default",
) -> dict[str, Any]:
    writer = BeaconCopywriter(workspace_id=workspace_id, user_id=user_id)
    voice = writer.load_brand_voice(client_id)
    if voice is None:
        raise HTTPException(status_code=404, detail="Brand voice not configured")
    return voice.to_dict()


@router.post("/beacon/campaign")
async def beacon_campaign(body: BeaconCampaignBody) -> dict[str, Any]:
    campaign = BeaconCampaign(workspace_id=body.workspace_id)
    plan = campaign.plan_campaign(
        campaign_name=body.campaign_name,
        objective=body.objective,
        client_name=body.client_name,
        channels=body.channels or None,
        duration_days=body.duration_days,
        audience=body.audience,
        key_message=body.key_message,
    )
    return plan.to_dict()


@router.post("/beacon/deliver")
async def beacon_deliver(body: BeaconDeliverBody) -> dict[str, Any]:
    delivery = BeaconDelivery(workspace_id=body.workspace_id, user_id=body.user_id)
    package = await delivery.prepare_deliverable(
        title=body.title,
        content=body.content,
        output_format=body.output_format,
        client_id=body.client_id,
        target_languages=body.target_languages,
        store=body.store,
    )
    return package.to_dict()


@router.post("/prism/audit")
async def prism_audit(body: PrismAuditBody) -> dict[str, Any]:
    seo = PrismSeo(workspace_id=body.workspace_id, user_id=body.user_id)
    report = await seo.audit_page(
        body.url,
        html_content=body.html_content,
        use_browser=body.use_browser and body.html_content is None,
        index_to_rag=body.index_to_rag,
    )
    return report.to_dict()


@router.post("/prism/brief")
async def prism_brief(body: PrismBriefBody) -> dict[str, Any]:
    seo = PrismSeo(workspace_id=body.workspace_id)
    brief = seo.build_content_brief(
        primary_keyword=body.primary_keyword,
        intent=body.intent,
        target_url=body.target_url,
        search_volume=body.search_volume,
        difficulty=body.difficulty,
        audience=body.audience or "Searchers looking for practical answers",
        competitor_gap=body.competitor_gap or "Competitors lack actionable checklists and updated examples.",
    )
    return brief.to_dict()


@router.post("/prism/keywords")
async def prism_keywords(body: PrismKeywordsBody) -> dict[str, Any]:
    keywords = PrismKeywords(workspace_id=body.workspace_id)
    entries = keywords.research_keywords(body.seed, limit=body.limit)
    clusters = keywords.cluster_keywords(entries)
    return {
        "keywords": [entry.to_dict() for entry in entries],
        "clusters": [cluster.to_dict() for cluster in clusters],
    }


@router.post("/prism/keywords/gap")
async def prism_keyword_gap(body: PrismGapBody) -> dict[str, Any]:
    keywords = PrismKeywords(workspace_id=body.workspace_id)
    return keywords.gap_analysis(
        body.seed,
        body.our_keywords,
        body.competitor_keywords,
        limit=body.limit,
    ).to_dict()


@router.post("/prism/social/calendar")
async def prism_social_calendar(body: PrismSocialBody) -> dict[str, Any]:
    social = PrismSocial(workspace_id=body.workspace_id)
    calendar = social.build_calendar(
        topic=body.topic,
        platforms=body.platforms or None,
        duration_days=body.duration_days,
    )
    return calendar.to_dict()


@router.post("/prism/analytics/report")
async def prism_analytics_report(body: PrismAnalyticsBody) -> dict[str, Any]:
    analytics = PrismAnalytics(workspace_id=body.workspace_id)
    report = analytics.build_performance_report(
        keyword_rankings=body.keyword_rankings or None,
        traffic_by_week=body.traffic_by_week or None,
        conversions_by_week=body.conversions_by_week or None,
        weeks=body.weeks,
    )
    return report.to_dict()


@router.post("/compass/clarify")
async def compass_clarify(body: CompassClarifyBody) -> dict[str, Any]:
    strategist = CompassStrategist(workspace_id=body.workspace_id)
    session = strategist.start_session(body.topic, extra_context=body.extra_context)
    return {
        "session_id": session.session_id,
        "topic": session.topic,
        "clarifying_questions": session.clarifying_questions,
        "minimum_answers_required": 3,
    }


@router.post("/compass/strategy")
async def compass_strategy(body: CompassStrategyBody) -> dict[str, Any]:
    strategist = CompassStrategist(workspace_id=body.workspace_id, user_id=body.user_id)
    return await strategist.run_strategy_session(
        body.topic,
        framework=body.framework,
        answers=body.answers,
        assumptions=body.assumptions or None,
        store=body.store,
    )


@router.post("/compass/analyze")
async def compass_analyze(body: CompassAnalyzeBody) -> dict[str, Any]:
    analyst = CompassAnalyst(workspace_id=body.workspace_id, user_id=body.user_id)
    analysis = await analyst.analyze_market(
        body.market,
        competitor_names=body.competitor_names or None,
        opportunity_artifacts=body.opportunity_artifacts or None,
        geography=body.geography,
        use_research=body.use_research,
        store=body.store,
    )
    return analysis.to_dict()


@router.post("/compass/decide")
async def compass_decide(body: CompassDecideBody) -> dict[str, Any]:
    decisions = CompassDecisions(workspace_id=body.workspace_id, user_id=body.user_id)
    result = decisions.evaluate_decision(
        body.decision_title,
        clarifying_answers=body.clarifying_answers,
        assumptions=body.assumptions or None,
        base_impact_usd=body.base_impact_usd,
        store=body.store,
    )
    return result.to_dict()


@router.post("/compass/scenarios")
async def compass_scenarios(body: CompassScenariosBody) -> dict[str, Any]:
    decisions = CompassDecisions(workspace_id=body.workspace_id)
    plan = decisions.plan_scenarios(
        body.decision_title,
        base_impact_usd=body.base_impact_usd,
        assumptions=body.assumptions or None,
    )
    return plan.to_dict()


@router.post("/ember/coach")
async def ember_coach(body: EmberCoachBody) -> dict[str, Any]:
    coach = EmberCoach(user_id=body.user_id)
    if body.store:
        response = await coach.coach_and_store(
            body.message,
            session_id=body.session_id,
            context=body.context,
            negative_checkin_streak=body.negative_checkin_streak,
        )
    else:
        response = coach.coach(
            body.message,
            session_id=body.session_id,
            context=body.context,
            negative_checkin_streak=body.negative_checkin_streak,
            store=False,
        )
    return response.to_dict()


@router.post("/ember/habits")
async def ember_create_habit(body: EmberHabitCreateBody) -> dict[str, Any]:
    habits = EmberHabits(workspace_id=body.workspace_id, user_id=body.user_id)
    record = await habits.create_habit(
        name=body.name,
        frequency=body.frequency,
        motivation=body.motivation,
        tiny_start=body.tiny_start,
        cue=body.cue,
        reward=body.reward,
    )
    return record.to_dict()


@router.post("/ember/habits/complete")
async def ember_complete_habit(body: EmberHabitCompleteBody) -> dict[str, Any]:
    habits = EmberHabits(workspace_id=body.workspace_id, user_id=body.user_id)
    try:
        record = await habits.log_completion(body.habit_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Habit not found") from None
    return record.to_dict()


@router.get("/ember/habits")
async def ember_list_habits(
    workspace_id: str = "default",
    user_id: str = "default",
) -> dict[str, Any]:
    habits = EmberHabits(workspace_id=workspace_id, user_id=user_id)
    rows = await habits.list_habits()
    return {"habits": [row.to_dict() for row in rows]}


@router.get("/ember/habits/{habit_id}/plan")
async def ember_habit_plan(
    habit_id: str,
    workspace_id: str = "default",
    user_id: str = "default",
) -> dict[str, Any]:
    habits = EmberHabits(workspace_id=workspace_id, user_id=user_id)
    try:
        plan = await habits.build_plan(habit_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Habit not found") from None
    return plan.to_dict()


@router.post("/ember/checkin")
async def ember_checkin(body: EmberCheckinBody) -> dict[str, Any]:
    checkin = EmberCheckin(user_id=body.user_id)
    record = await checkin.submit_checkin(
        energy=body.energy,
        stress=body.stress,
        focus=body.focus,
        sleep=body.sleep,
        mood=body.mood,
        notes=body.notes,
    )
    return record.to_dict()


@router.get("/ember/checkin/history")
async def ember_checkin_history(user_id: str = "default", limit: int = 30) -> dict[str, Any]:
    checkin = EmberCheckin(user_id=user_id)
    rows = await checkin.list_checkins(limit=limit)
    return {"checkins": [row.to_dict() for row in rows]}


@router.post("/ember/checkin/schedule")
async def ember_schedule_checkin(body: EmberCheckinScheduleBody) -> dict[str, Any]:
    checkin = EmberCheckin(user_id=body.user_id)
    schedule = checkin.schedule_checkins(frequency=body.frequency, topics=body.topics or None)
    return schedule.to_dict()


@router.get("/ember/checkin/burnout")
async def ember_burnout_assessment(user_id: str = "default") -> dict[str, Any]:
    checkin = EmberCheckin(user_id=user_id)
    return await checkin.burnout_assessment()


@router.post("/codex/review")
async def codex_review(body: CodexReviewBody) -> dict[str, Any]:
    reviewer = CodexReviewer(workspace_id=body.workspace_id, user_id=body.user_id)
    review = await reviewer.review_contract(
        title=body.title,
        text=body.text,
        jurisdiction=body.jurisdiction,
        store=body.store,
        index_to_rag=body.index_to_rag,
    )
    return review.to_dict()


@router.post("/codex/draft")
async def codex_draft(body: CodexDraftBody) -> dict[str, Any]:
    drafter = CodexDrafter(workspace_id=body.workspace_id, user_id=body.user_id)
    try:
        draft = drafter.draft_document(
            document_type=body.document_type,
            title=body.title,
            jurisdiction=body.jurisdiction,
            parties=body.parties or None,
            store=body.store,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return draft.to_dict()


@router.post("/codex/ask")
async def codex_ask(body: CodexAskBody) -> dict[str, Any]:
    researcher = CodexResearcher(workspace_id=body.workspace_id, user_id=body.user_id)
    return researcher.answer_question(body.question, jurisdiction=body.jurisdiction).to_dict()


@router.post("/codex/regulatory")
async def codex_regulatory(body: CodexRegulatoryBody) -> dict[str, Any]:
    researcher = CodexResearcher(workspace_id=body.workspace_id, user_id=body.user_id)
    update = await researcher.track_regulatory_changes(
        body.topic,
        jurisdiction=body.jurisdiction,
        use_research=body.use_research,
        store=body.store,
    )
    return update.to_dict()


@router.post("/codex/checklist")
async def codex_checklist(body: CodexChecklistBody) -> dict[str, Any]:
    researcher = CodexResearcher()
    return researcher.generate_checklist(body.checklist_type, jurisdiction=body.jurisdiction)


@router.get("/governance/status")
async def governance_status(workspace_id: str = "default", user_id: str = "default") -> dict[str, Any]:
    bridge = GovernancePolicyBridge(workspace_id=workspace_id, user_id=user_id)
    return await bridge.governance_status()


@router.post("/governance/checkpoint")
async def governance_checkpoint(body: GovernanceCheckpointBody) -> dict[str, Any]:
    bridge = GovernancePolicyBridge(workspace_id=body.workspace_id, user_id=body.user_id)
    return bridge.evaluate_tool_execution(body.tool_name, persona=body.persona).to_dict()


@router.post("/governance/kill")
async def governance_kill(body: GovernanceKillBody) -> dict[str, Any]:
    bridge = GovernancePolicyBridge(workspace_id=body.workspace_id, user_id=body.user_id)
    try:
        return bridge.activate_kill_switch(
            body.level,
            reason=body.reason,
            propagate_scheduler=body.propagate_scheduler,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/governance/kill/clear")
async def governance_kill_clear(
    workspace_id: str = "default",
    user_id: str = "default",
    clear_scheduler: bool = False,
) -> dict[str, Any]:
    bridge = GovernancePolicyBridge(workspace_id=workspace_id, user_id=user_id)
    return bridge.clear_kill_switch(clear_scheduler=clear_scheduler)


@router.post("/governance/audit")
async def governance_audit(body: GovernanceAuditBody) -> dict[str, Any]:
    bridge = GovernancePolicyBridge(workspace_id=body.workspace_id, user_id=body.user_id)
    return await bridge.stream_audit_event(body.event_type, body.payload)


@router.get("/governance/compliance/{framework}")
async def governance_compliance(framework: str) -> dict[str, Any]:
    bridge = GovernancePolicyBridge()
    return bridge.compliance_export_template(framework)


@router.post("/governance/evidence-pack")
async def governance_evidence_pack(body: GovernanceEvidenceBody) -> dict[str, Any]:
    bridge = GovernancePolicyBridge(workspace_id=body.workspace_id, user_id=body.user_id)
    pack = await bridge.build_evidence_pack(limit=body.limit)
    return pack.to_dict()


@router.post("/governance/connector")
async def governance_connector(body: GovernanceConnectorBody) -> dict[str, Any]:
    bridge = GovernancePolicyBridge(workspace_id=body.workspace_id, user_id=body.user_id)
    return await bridge.connector_handoff(body.action)


@router.post("/echo/webhook")
async def echo_webhook(body: EchoWebhookBody) -> dict[str, Any]:
    profile = BusinessProfile()
    receptionist = EchoReceptionist(
        workspace_id=body.workspace_id,
        user_id=body.user_id,
        profile=profile,
    )
    turn = await receptionist.handle_inbound_webhook(body.payload)
    return turn.to_dict()


@router.post("/echo/book")
async def echo_book(body: EchoBookBody) -> dict[str, Any]:
    receptionist = EchoReceptionist(workspace_id=body.workspace_id, user_id=body.user_id)
    turn = await receptionist.book_from_session(body.call_id, slot_index=body.slot_index, title=body.title)
    return turn.to_dict()


@router.post("/echo/ask")
async def echo_ask(body: EchoAskBody) -> dict[str, Any]:
    profile = BusinessProfile(
        business_name=body.business_name,
        hours=body.hours,
        location=body.location,
    )
    knowledge = EchoKnowledge(workspace_id=body.workspace_id, user_id=body.user_id, profile=profile)
    answer = await knowledge.answer_question(body.question)
    return answer.to_dict()


@router.post("/echo/slots")
async def echo_slots(body: EchoSlotsBody) -> dict[str, Any]:
    scheduler = EchoScheduler(workspace_id=body.workspace_id, user_id=body.user_id)
    slots = scheduler.find_available_slots(days=body.days, count=body.count)
    return {"slots": [slot.to_dict() for slot in slots]}


@router.get("/echo/greeting")
async def echo_greeting(
    business_name: str = "Your Business",
    caller_name: str = "",
    workspace_id: str = "default",
    user_id: str = "default",
) -> dict[str, Any]:
    profile = BusinessProfile(business_name=business_name)
    receptionist = EchoReceptionist(workspace_id=workspace_id, user_id=user_id, profile=profile)
    reply = receptionist.greeting(caller_name=caller_name)
    return {"greeting": reply, "voice": receptionist.build_voice_gateway_response(reply)}
