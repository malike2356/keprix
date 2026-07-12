"""Pydantic schema for product billing.yaml configuration."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ProductConfig(BaseModel):
    id: str
    name: str
    company: str
    company_address: str = ""
    vat_number: str = ""
    support_email: str = ""
    website: str = ""
    trial_days: int = 0


class PlanPriceConfig(BaseModel):
    amount: int = Field(..., ge=0)
    currency: str = "gbp"
    interval: Literal["month", "year"] | None = None
    discount_text: str | None = None
    # Existing Stripe Price ID from verlox/.stripe-credentials-and-price-id.md.
    # Required for live Stripe; agents must never create new Stripe prices.
    stripe_price_id: str | None = None


class PlanConfig(BaseModel):
    id: str
    name: str
    description: str = ""
    price: int | None = None
    currency: str = "gbp"
    interval: Literal["month", "year"] | None = None
    prices: list[PlanPriceConfig] = Field(default_factory=list)
    seats: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
    feature_flags: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_prices(self) -> PlanConfig:
        if self.price is not None and not self.prices:
            self.prices = [
                PlanPriceConfig(
                    amount=self.price,
                    currency=self.currency,
                    interval=self.interval,
                )
            ]
        return self

    def resolved_prices(self) -> list[PlanPriceConfig]:
        if self.prices:
            return self.prices
        if self.price is not None:
            return [
                PlanPriceConfig(
                    amount=self.price,
                    currency=self.currency,
                    interval=self.interval,
                )
            ]
        return []


class AddonConfig(BaseModel):
    id: str
    name: str
    description: str = ""
    price: int
    currency: str = "gbp"
    interval: Literal["month", "year"] = "month"
    applies_to: list[str] = Field(default_factory=list)
    stripe_price_id: str | None = None


class DonationConfig(BaseModel):
    id: str = "coffee"
    name: str = "Buy me a coffee"
    description: str = "Optional open-amount donation from £1. Not required."
    amount: int = 100
    currency: str = "gbp"
    stripe_price_id: str


class TaxRegionConfig(BaseModel):
    code: str
    name: str
    rate: float | None = None
    rule: Literal["always", "b2b_reverse", "none"] = "none"
    vat_validation: Literal["hmrc", "vies", "none"] = "none"


class TaxConfig(BaseModel):
    regions: list[TaxRegionConfig] = Field(default_factory=list)


class DunningStepConfig(BaseModel):
    days: int
    action: Literal["retry", "cancel"] = "retry"
    notify: bool = False
    notify_template: str | None = None
    degrade_features: bool = False


class DunningConfig(BaseModel):
    enabled: bool = True
    retry_schedule: list[DunningStepConfig] = Field(default_factory=list)


class WebhookConfig(BaseModel):
    signing_secret_env: str = "STRIPE_WEBHOOK_SECRET"
    events: list[str] = Field(default_factory=list)


class AiWalletConfig(BaseModel):
    """Managed AI credit wallet defaults for hosted deployments."""

    enabled: bool = True
    markup: float = 2.0
    trial_credits: int = 500
    trial_daily_cap_credits: int = 100
    # Existing Verlox top-up price IDs only (from .stripe-credentials-and-price-id.md).
    topup_price_ids: list[str] = Field(
        default_factory=lambda: [
            "price_1TrhlN2WMXleLh8enqPqXHs5",  # Pay £5 to Verlox
            "price_1Trhnl2WMXleLh8e2zddW2ET",  # Pay £10 to Verlox
            "price_1Trho42WMXleLh8ekL7R7Vq7",  # Pay £20 to Verlox
        ]
    )


class BillingConfig(BaseModel):
    product: ProductConfig
    plans: list[PlanConfig]
    addons: list[AddonConfig] = Field(default_factory=list)
    donations: list[DonationConfig] = Field(default_factory=list)
    tax: TaxConfig = Field(default_factory=TaxConfig)
    dunning: DunningConfig = Field(default_factory=DunningConfig)
    webhooks: WebhookConfig = Field(default_factory=WebhookConfig)
    ai_wallet: AiWalletConfig = Field(default_factory=AiWalletConfig)

    @field_validator("plans")
    @classmethod
    def require_plans(cls, value: list[PlanConfig]) -> list[PlanConfig]:
        if not value:
            raise ValueError("At least one plan is required")
        return value

    def plan_by_id(self, plan_id: str) -> PlanConfig | None:
        for plan in self.plans:
            if plan.id == plan_id:
                return plan
        return None

    def donation_by_id(self, donation_id: str) -> DonationConfig | None:
        for donation in self.donations:
            if donation.id == donation_id:
                return donation
        return None

    def community_plan(self) -> PlanConfig | None:
        for plan in self.plans:
            if plan.id == "community" or (plan.resolved_prices() and plan.resolved_prices()[0].amount == 0):
                return plan
        return self.plans[0] if self.plans else None
