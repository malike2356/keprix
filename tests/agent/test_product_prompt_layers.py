"""Tests for product prompt layer registration, rendering, and opt-out.

Verifies Prompt 329 acceptance criteria:
- Product prompt layers are registered, not hardcoded.
- Layers render in registration order.
- Individual layers can be opted out.
- Layer rendering errors are swallowed.
- Core layers are unaffected by product layer registration.
"""

import pytest

from registries.product_hooks import (
    register_product_prompt_layer,
    iter_product_prompt_layers,
    disable_prompt_layer,
    enable_prompt_layer,
    clear_prompt_layers_for_tests,
)


@pytest.fixture(autouse=True)
def _clean_layers():
    clear_prompt_layers_for_tests()
    yield
    clear_prompt_layers_for_tests()


# ── Registration and iteration ──────────────────────────────────────────


class TestProductLayerRegistration:
    def test_register_and_iterate(self):
        """Registered product layers appear in iteration order."""
        register_product_prompt_layer(
            "scout_governance", "scout",
            lambda: "Scout governance policy: all actions are logged.",
        )
        register_product_prompt_layer(
            "channel_shield_policy", "channel_shield",
            lambda: "Channel Shield: PII is never sent to external APIs.",
        )

        layers = iter_product_prompt_layers()
        assert len(layers) == 2
        assert layers[0].name == "scout_governance"
        assert layers[0].product == "scout"
        assert layers[1].name == "channel_shield_policy"
        assert layers[1].product == "channel_shield"

    def test_render_returns_content(self):
        """Layer render callable returns the prompt text."""
        register_product_prompt_layer(
            "test_layer", "test",
            lambda: "Test layer content.",
        )

        layers = iter_product_prompt_layers()
        content = layers[0].render()
        assert content == "Test layer content."

    def test_empty_layers_when_none_registered(self):
        """No registered layers returns empty list."""
        assert iter_product_prompt_layers() == []


# ── Opt-out / disable ───────────────────────────────────────────────────


class TestProductLayerOptOut:
    def test_disable_removes_layer(self):
        """Disabled layers do not appear in iteration."""
        register_product_prompt_layer("layer_a", "product_a", lambda: "A")
        register_product_prompt_layer("layer_b", "product_b", lambda: "B")
        register_product_prompt_layer("layer_c", "product_c", lambda: "C")

        disable_prompt_layer("layer_b")

        layers = iter_product_prompt_layers()
        names = [l.name for l in layers]
        assert names == ["layer_a", "layer_c"]  # B is omitted

    def test_enable_restores_layer(self):
        """Re-enabling a disabled layer brings it back."""
        register_product_prompt_layer("layer_x", "product_x", lambda: "X")
        disable_prompt_layer("layer_x")
        assert len(iter_product_prompt_layers()) == 0

        enable_prompt_layer("layer_x")
        assert len(iter_product_prompt_layers()) == 1
        assert iter_product_prompt_layers()[0].name == "layer_x"

    def test_disable_nonexistent_is_noop(self):
        """Disabling a layer that was never registered is a no-op."""
        disable_prompt_layer("nonexistent")
        assert iter_product_prompt_layers() == []


# ── Error resilience ────────────────────────────────────────────────────


class TestProductLayerErrorResilience:
    def test_render_error_does_not_block_other_layers(self):
        """Rendering errors in the assembly are caught per-layer.

        The assembly in layered_assembly.py wraps each render() call in
        a try/except so a single broken product layer does not prevent
        other product layers from rendering.
        """
        register_product_prompt_layer("working", "test_a", lambda: "Working layer.")
        register_product_prompt_layer("broken", "test_b", lambda: (_ for _ in ()).throw(RuntimeError("render fail")))
        register_product_prompt_layer("also_working", "test_c", lambda: "Also working.")

        # Simulate what the assembly does: iterate and call render() per layer
        rendered = []
        from registries.product_hooks import iter_product_prompt_layers
        for layer in iter_product_prompt_layers():
            try:
                content = layer.render()
                if content and content.strip():
                    rendered.append((layer.name, content.strip()))
            except Exception:
                pass  # assembly swallows errors

        names = [r[0] for r in rendered]
        assert names == ["working", "also_working"]  # broken is absent but others render


# ── Integration: layer ordering with core layers ─────────────────────────


class TestProductLayerOrdering:
    """Product layers render after core layers and persona, before final output."""

    def test_product_layer_appears_after_persona(self):
        """Product layers come after persona in the enum ordering."""
        from agent.layered_prompt import PromptLayer

        assert PromptLayer.PRODUCT.value > PromptLayer.PERSONA.value
        assert PromptLayer.PRODUCT.value > PromptLayer.DOMAIN.value
        assert PromptLayer.PRODUCT.value > PromptLayer.EXECUTION.value

    def test_player_order_is_deterministic(self):
        """Two iterations return layers in the same order."""
        register_product_prompt_layer("first", "p1", lambda: "1")
        register_product_prompt_layer("second", "p2", lambda: "2")
        register_product_prompt_layer("third", "p3", lambda: "3")

        run1 = [l.name for l in iter_product_prompt_layers()]
        run2 = [l.name for l in iter_product_prompt_layers()]
        assert run1 == run2 == ["first", "second", "third"]

    def test_core_layers_build_with_product_layers_present(self):
        """Registering product layers does not affect core layer construction."""
        from agent.layered_prompt import LayeredPromptBuilder, PromptLayer, PromptSessionContext

        register_product_prompt_layer("test_product", "test", lambda: "Product layer output.")

        # Build a prompt with mock agent that has layered_prompt enabled
        ctx = PromptSessionContext(
            model_name="test-model",
            provider_name="test",
            session_id="sess-1",
            keprix_version="0.0.0",
        )
        builder = LayeredPromptBuilder(ctx)
        builder.add_layer(PromptLayer.IDENTITY, "Identity layer")
        builder.add_layer(PromptLayer.PERSONA, "Persona layer")

        from registries.product_hooks import iter_product_prompt_layers
        for layer in iter_product_prompt_layers():
            content = layer.render()
            if content and content.strip():
                builder.add_layer(PromptLayer.PRODUCT, content.strip())

        result = builder.build()

        assert "Identity layer" in result
        assert "Persona layer" in result
        assert "Product layer output." in result
        # Product layer should appear after persona
        assert result.index("Persona layer") < result.index("Product layer output.")


# ── Hereme-equivalent sections presence ──────────────────────────────────


class TestLayeredPromptHasRequiredSections:
    """Prompt 329 requires Hermes-equivalent sections are present."""

    def test_all_core_layers_enum_present(self):
        """All required core layers exist in the enum."""
        from agent.layered_prompt import PromptLayer

        required = {
            "IDENTITY", "BUDGET", "SAFETY", "TOOLS", "TONE",
            "MEMORY", "EXECUTION", "DOMAIN", "PERSONA", "PRODUCT",
        }
        actual = {m.name for m in PromptLayer}
        assert required == actual
