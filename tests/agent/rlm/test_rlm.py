import pytest

from keprix.agent.rlm import ContextTree, RlmBudget, RecursiveModel


def test_context_tree_pruning_does_not_mutate_messages() -> None:
    messages = [{"role": "user", "content": "keep"}, {"role": "assistant", "content": "drop"}]
    tree = ContextTree()
    tree.build(messages)
    tree.prune(tree.nodes[tree.root_id].children[1])
    assert tree.subset(tree.root_id) == [messages[0]]
    assert messages == [{"role": "user", "content": "keep"}, {"role": "assistant", "content": "drop"}]
    tree.expand(tree.nodes[tree.root_id].children[1])
    assert tree.subset(tree.root_id) == messages


@pytest.mark.asyncio
async def test_recursive_model_uses_leaf_model_and_hard_budget() -> None:
    calls = []

    async def provider(model, context, instruction, depth):
        calls.append((model, context, instruction, depth))
        return "bounded result"

    runtime = RecursiveModel(provider, model="parent", leaf_model="cheap", budget=RlmBudget(max_depth=1, max_calls=1, max_output_tokens=20))
    result = await runtime.call([{"role": "user", "content": "part"}], "solve", depth=1)
    assert result.ok and result.model == "cheap"
    assert calls[0][1] == [{"role": "user", "content": "part"}]
    blocked = await runtime.call([], "again", depth=1)
    assert blocked.truncated and blocked.value["error"] == "rlm_budget_exhausted"
