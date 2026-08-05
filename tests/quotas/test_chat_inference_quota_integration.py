import pytest

from keprix.api import chat_inference
from keprix.quotas.quota_config import ProductQuota, ResourceType, get_quota_config
from keprix.quotas.runtime import get_quota_store
from keprix.security.product_context import ProductContext, clear_product_context, set_product_context


@pytest.mark.asyncio
async def test_stream_chat_completion_records_product_quota(monkeypatch) -> None:
    product_id = "quota-chat-test"
    get_quota_config().register(
        ProductQuota(
            product_id=product_id,
            limits={
                ResourceType.LLM_TOKENS_IN: 10_000,
                ResourceType.LLM_TOKENS_OUT: 10_000,
                ResourceType.CONCURRENT_SESSIONS: 2,
            },
        )
    )

    async def fake_stream(client, resolved_model, messages, usage_holder):
        usage_holder.update({"input_tokens": 7, "output_tokens": 3, "total_tokens": 10})
        yield "hello"

    monkeypatch.setattr(chat_inference, "_provider_configured", lambda provider: True)
    monkeypatch.setattr(chat_inference, "parse_model_id", lambda model_id: ("deepseek", "deepseek-chat"))
    monkeypatch.setattr(chat_inference, "_stream_via_thread", fake_stream)
    monkeypatch.setattr("agent.auxiliary_client.resolve_provider_client", lambda provider, model, async_mode=True: (object(), model))

    token = set_product_context(ProductContext(product_id=product_id, workspace_id="default"))
    try:
        chunks = [
            chunk
            async for chunk in chat_inference.stream_chat_completion(
                user_text="hello",
                model_id="deepseek:deepseek-chat",
                history=[],
                include_codebase_context=False,
            )
        ]
    finally:
        clear_product_context(token)

    usage = await get_quota_store().get_usage(product_id)
    assert chunks == ["hello"]
    assert usage.used(ResourceType.LLM_TOKENS_IN) == 7
    assert usage.used(ResourceType.LLM_TOKENS_OUT) == 3
