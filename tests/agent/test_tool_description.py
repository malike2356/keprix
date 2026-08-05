"""Tests for natural language tool descriptions."""

from __future__ import annotations

from agent.tool_description import generate_natural_description
from agent.tool_schema import ParameterSchema, ReturnSchema, ToolExample, ToolSchema


def test_generate_natural_description_includes_params_and_example():
    tool = ToolSchema(
        name="stripe.create_payment",
        description="Create a Stripe payment intent.",
        parameters={
            "amount": ParameterSchema(
                name="amount",
                type="number",
                description="Amount in minor units.",
            ),
            "currency": ParameterSchema(
                name="currency",
                type="string",
                description="ISO currency code.",
                enum=["gbp", "usd"],
            ),
        },
        returns=ReturnSchema(type="json", description="Payment intent payload."),
        examples=[
            ToolExample(
                description="Charge a customer fifty pounds",
                parameters={"amount": 5000, "currency": "gbp"},
                result_summary="Payment intent created.",
            )
        ],
    )
    text = generate_natural_description(tool)
    assert "stripe.create_payment" in text
    assert "amount (number, required)" in text
    assert "Must be one of: gbp, usd" in text
    assert "Charge a customer fifty pounds" in text
