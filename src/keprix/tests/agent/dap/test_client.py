import pytest

from agent.dap.client import DapClient, DapError


@pytest.mark.asyncio
async def test_request_requires_running_adapter() -> None:
    with pytest.raises(DapError, match="not running"):
        await DapClient(["missing"]).request("threads")


@pytest.mark.asyncio
async def test_stop_is_idempotent() -> None:
    client = DapClient(["missing"])
    await client.stop()
    await client.stop()
