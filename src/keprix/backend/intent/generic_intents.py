"""Built-in generic intent schemas."""

from __future__ import annotations

from keprix.backend.intent.schemas import EntitySchema, IntentSchema

GENERIC_INTENTS: list[IntentSchema] = [
    IntentSchema(
        name="ask_question",
        description="The user is asking for information or an explanation.",
        domain="generic",
        entities=[
            EntitySchema(
                name="topic",
                type="string",
                required=False,
                description="The subject the user is asking about",
            ),
        ],
        follow_up_template="Could you tell me more about what you need to know regarding {missing_fields}?",
        examples=["What is the water table depth here?", "How much does this cost?"],
    ),
    IntentSchema(
        name="make_request",
        description="The user wants something done: a quote, a visit, a report, a calculation.",
        domain="generic",
        entities=[
            EntitySchema(
                name="request_type",
                type="string",
                required=True,
                description="What the user wants done",
            ),
            EntitySchema(
                name="target",
                type="string",
                required=False,
                description="What the request is for",
            ),
        ],
        follow_up_template="What would you like me to do with {missing_fields}?",
    ),
    IntentSchema(
        name="provide_information",
        description="The user is supplying information requested in a previous turn.",
        domain="generic",
        entities=[
            EntitySchema(name="information_type", type="string", required=False),
            EntitySchema(name="value", type="string", required=True),
        ],
        follow_up_template="",
    ),
    IntentSchema(
        name="confirm",
        description="The user is confirming, agreeing, or saying yes.",
        domain="generic",
        entities=[],
        follow_up_template="",
        examples=["Yes", "That is correct", "Aane", "Yoo"],
    ),
    IntentSchema(
        name="cancel",
        description="The user is cancelling, stopping, or saying no.",
        domain="generic",
        entities=[],
        follow_up_template="",
        examples=["No", "Stop", "Cancel", "Daabi"],
    ),
    IntentSchema(
        name="request_help",
        description="The user needs help or does not understand.",
        domain="generic",
        entities=[],
        follow_up_template="",
    ),
    IntentSchema(
        name="greeting",
        description="The user is greeting or starting a conversation.",
        domain="generic",
        entities=[],
        follow_up_template="",
    ),
    IntentSchema(
        name="fallback",
        description="The input did not match any specific intent with sufficient confidence.",
        domain="generic",
        entities=[
            EntitySchema(name="raw_query", type="string", required=False),
        ],
        follow_up_template="I was not sure what you needed. Could you tell me more about {missing_fields}?",
    ),
]
