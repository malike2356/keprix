"""Twilio phone number provisioning plans for Aiva workers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProvisionedPhoneNumber:
    worker_id: str
    phone_number: str
    voice_url: str
    status_url: str


class PhoneProvisioner:
    def __init__(self, *, base_url: str = "https://core.keprix.ai") -> None:
        self.base_url = base_url.rstrip("/")
        self._assignments: dict[str, ProvisionedPhoneNumber] = {}

    async def provision_for_worker(self, worker_id: str, country: str = "GB", area_code: str | None = None) -> str:
        suffix = area_code or country
        phone = f"+1000{abs(hash((worker_id, suffix))) % 1000000:06d}"
        record = ProvisionedPhoneNumber(
            worker_id=worker_id,
            phone_number=phone,
            voice_url=f"{self.base_url}/api/voice/inbound",
            status_url=f"{self.base_url}/api/voice/status",
        )
        self._assignments[worker_id] = record
        return phone

    async def release_for_worker(self, worker_id: str) -> bool:
        return self._assignments.pop(worker_id, None) is not None

    def get_assignment(self, worker_id: str) -> ProvisionedPhoneNumber | None:
        return self._assignments.get(worker_id)
