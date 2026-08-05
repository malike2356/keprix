"""Campaign planning and asset management for BEACON."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from keprix.compat import UTC
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix.opportunity.playbooks.asset_factory import DEFAULT_ASSET_FILES
from keprix.personas.beacon.persona import BEACON_PERSONA

DEFAULT_CHANNELS = ("email", "social", "landing", "ads", "blog")

CHANNEL_ASSET_MAP: dict[str, list[str]] = {
    "email": ["email-nurture-sequence.md"],
    "social": ["linkedin-posts.md", "short-video-scripts.md"],
    "landing": ["landing-page.md"],
    "ads": ["ad-copy.md"],
    "blog": ["lead-magnet.md", "08-content-assets.md"],
    "sales": ["sales-deck.md", "10-sales-deck.md"],
}


@dataclass(slots=True)
class CampaignAsset:
    channel: str
    title: str
    due_date: str
    status: str = "planned"
    owner: str = "BEACON"
    opportunity_asset: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "title": self.title,
            "due_date": self.due_date,
            "status": self.status,
            "owner": self.owner,
            "opportunity_asset": self.opportunity_asset,
        }


@dataclass
class CampaignPlan:
    campaign_id: str
    campaign_name: str
    objective: str
    client_name: str
    channels: list[str]
    assets: list[CampaignAsset] = field(default_factory=list)
    duration_days: int = 14
    brief_markdown: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "objective": self.objective,
            "client_name": self.client_name,
            "channels": list(self.channels),
            "assets": [asset.to_dict() for asset in self.assets],
            "duration_days": self.duration_days,
            "brief_markdown": self.brief_markdown,
        }


class BeaconCampaign:
    def __init__(self, *, workspace_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.persona = BEACON_PERSONA
        self._template_path = Path(__file__).resolve().parent / "prompts" / "campaign_brief.md"

    def opportunity_assets_for_channels(self, channels: list[str]) -> list[str]:
        assets: list[str] = []
        for channel in channels:
            for asset_name in CHANNEL_ASSET_MAP.get(channel, []):
                if asset_name not in assets:
                    assets.append(asset_name)
        if not assets:
            assets = list(DEFAULT_ASSET_FILES[:4])
        return assets

    def build_asset_calendar(
        self,
        *,
        campaign_name: str,
        channels: list[str],
        duration_days: int,
        start_date: datetime | None = None,
    ) -> list[CampaignAsset]:
        start = start_date or datetime.now(UTC)
        assets: list[CampaignAsset] = []
        opportunity_assets = self.opportunity_assets_for_channels(channels)
        slot_days = max(1, duration_days // max(len(channels), 1))

        for index, channel in enumerate(channels):
            due = start + timedelta(days=index * slot_days)
            linked = opportunity_assets[index % len(opportunity_assets)] if opportunity_assets else None
            assets.append(
                CampaignAsset(
                    channel=channel,
                    title=f"{campaign_name} - {channel} asset",
                    due_date=due.date().isoformat(),
                    opportunity_asset=linked,
                )
            )
            assets.append(
                CampaignAsset(
                    channel=channel,
                    title=f"{campaign_name} - {channel} review",
                    due_date=(due + timedelta(days=1)).date().isoformat(),
                    status="review",
                    opportunity_asset=linked,
                )
            )
        return assets

    def render_brief(self, plan: CampaignPlan, *, audience: str = "", key_message: str = "") -> str:
        template = self._template_path.read_text(encoding="utf-8")
        calendar_rows = "\n".join(
            f"| {asset.due_date} | {asset.channel} | {asset.title} | {asset.owner} | {asset.status} |"
            for asset in plan.assets
        ) or "| - | - | - | - | - |"
        channel_plan = "\n".join(
            f"- **{channel}**: {', '.join(CHANNEL_ASSET_MAP.get(channel, ['custom asset']))}"
            for channel in plan.channels
        )
        replacements = {
            "{{campaign_name}}": plan.campaign_name,
            "{{objective}}": plan.objective,
            "{{client_name}}": plan.client_name,
            "{{duration_days}}": str(plan.duration_days),
            "{{channels}}": ", ".join(plan.channels),
            "{{audience}}": audience or "Primary ICP segment",
            "{{key_message}}": key_message or plan.objective,
            "{{metrics}}": "CTR, conversion rate, qualified leads",
            "{{calendar_rows}}": calendar_rows,
            "{{channel_plan}}": channel_plan,
            "{{legal_review}}": "yes" if "ads" in plan.channels else "no",
            "{{client_signoff}}": "yes",
        }
        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(key, value)
        return rendered

    def plan_campaign(
        self,
        *,
        campaign_name: str,
        objective: str,
        client_name: str,
        channels: list[str] | None = None,
        duration_days: int = 14,
        audience: str = "",
        key_message: str = "",
    ) -> CampaignPlan:
        selected_channels = list(channels or DEFAULT_CHANNELS[:3])
        assets = self.build_asset_calendar(
            campaign_name=campaign_name,
            channels=selected_channels,
            duration_days=duration_days,
        )
        plan = CampaignPlan(
            campaign_id=str(uuid4()),
            campaign_name=campaign_name,
            objective=objective,
            client_name=client_name,
            channels=selected_channels,
            assets=assets,
            duration_days=duration_days,
        )
        plan.brief_markdown = self.render_brief(plan, audience=audience, key_message=key_message)
        return plan
