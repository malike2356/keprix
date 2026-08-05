import pytest

from keprix.voice.phone_provisioning import PhoneProvisioner


@pytest.mark.asyncio
async def test_phone_provisioner_assigns_and_releases_number() -> None:
    provisioner = PhoneProvisioner(base_url="https://voice.example.test")

    number = await provisioner.provision_for_worker("worker-1", country="GB")
    assignment = provisioner.get_assignment("worker-1")

    assert number.startswith("+1000")
    assert assignment is not None
    assert assignment.voice_url == "https://voice.example.test/api/voice/inbound"
    assert await provisioner.release_for_worker("worker-1")
