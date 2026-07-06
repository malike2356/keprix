"""BEACON marketing persona package."""

from keprix.personas.beacon.campaign import BeaconCampaign, CampaignPlan
from keprix.personas.beacon.copywriter import BeaconCopywriter, BrandVoice, CopyResult
from keprix.personas.beacon.delivery import BeaconDelivery, DeliverablePackage
from keprix.personas.beacon.persona import BEACON_PERSONA

__all__ = [
    "BEACON_PERSONA",
    "BeaconCampaign",
    "BeaconCopywriter",
    "BeaconDelivery",
    "BrandVoice",
    "CampaignPlan",
    "CopyResult",
    "DeliverablePackage",
]
