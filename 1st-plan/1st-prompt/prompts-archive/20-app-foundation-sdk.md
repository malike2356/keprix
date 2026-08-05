# keprix - Prompt 20: App Foundation SDK and Natural Language CRUD

## Context

This prompt introduces a new first-class feature unique to keprix: the App Foundation
SDK. It is not ported from any of the three source projects. Build it fresh.

The SDK is the mechanism by which third-party applications embed keprix as their AI
control layer. An app registers its domain schema once at startup. From that point on,
users can control the app with natural language through any connected channel (Telegram,
web chat, email, etc.) and keprix executes the correct structured actions.

Output directories:
- `keprix/keprix_sdk/python/` - Python SDK package
- `keprix/keprix_sdk/typescript/` - TypeScript/Node.js SDK package
- `keprix/backend/sdk/` - Backend routes that power the SDK

## What the SDK Does (Overview)

1. App developer imports `CarinaApp` from the SDK
2. Developer defines their domain: entities, operations, field types, validation
3. Developer calls `app.connect(keprix_url, api_token)` at startup
4. keprix registers the app's schema in its context
5. When a user sends a message (any channel), keprix checks if it matches a
   registered app's domain, constructs a structured action plan, and returns it
6. The SDK delivers the action plan to the app's registered callback
7. The app executes the actions against its own database

The SDK is MIT licensed. Apps call the keprix backend over HTTP. The AGPL
backend source code is not embedded in the SDK.

## Python SDK Package

### Location

```
keprix/keprix_sdk/python/
  pyproject.toml        - package name: keprix-sdk, version: 1.0.0
  src/
    keprix_sdk/
      __init__.py       - exports CarinaApp, Domain, Entity, Field, Operation
      app.py            - CarinaApp class
      domain.py         - Domain, Entity, Field, Operation classes
      schema.py         - schema serialiser (to JSON for API)
      client.py         - HTTP client wrapping the keprix backend
      types.py          - ActionPlan, ActionStep, ExecutionResult type definitions
  README.md
  examples/
    invoice_app.py      - complete working example
    crm_app.py          - complete working example
```

### `CarinaApp` Class (Python)

```python
from keprix_sdk import CarinaApp, Domain, Entity, Field, Operation

app = CarinaApp(
    name="my-invoicing-app",
    carina_url="http://localhost:3333",
    api_token="carina_tok_...",
)

# Define the domain
invoice_domain = Domain(
    name="invoicing",
    entities=[
        Entity(
            name="Client",
            fields=[
                Field("name", type="string", required=True),
                Field("email", type="email", required=True),
                Field("company", type="string"),
            ],
            operations=[
                Operation("create", confirmation_required=False),
                Operation("read", confirmation_required=False),
                Operation("update", confirmation_required=False),
                Operation("delete", confirmation_required=True),  # destructive
            ],
        ),
        Entity(
            name="Invoice",
            fields=[
                Field("client_id", type="foreign_key", entity="Client", required=True),
                Field("amount", type="decimal", required=True),
                Field("currency", type="string", default="GBP"),
                Field("due_date", type="date"),
                Field("status", type="enum", values=["draft","sent","paid","overdue"]),
            ],
            operations=[
                Operation("create"),
                Operation("read"),
                Operation("update"),
                Operation("send", confirmation_required=True),
                Operation("mark_paid"),
                Operation("delete", confirmation_required=True),
            ],
        ),
    ],
)

app.register_domain(invoice_domain)

# Register action callback - called when keprix parses a user instruction
@app.on_action
def handle_action(plan: ActionPlan) -> ExecutionResult:
    for step in plan.steps:
        if step.entity == "Client" and step.operation == "create":
            client = db.create_client(
                name=step.fields["name"],
                email=step.fields["email"],
            )
            step.result = {"id": client.id, "status": "created"}
        elif step.entity == "Invoice" and step.operation == "send":
            invoice = db.get_invoice(step.fields["invoice_id"])
            email_service.send(invoice)
            step.result = {"status": "sent"}
        # ... other operations
    return ExecutionResult(success=True, steps=plan.steps)

# Start listening (blocks, runs async event loop)
app.start()
```

### `ActionPlan` Type

```python
@dataclass
class ActionStep:
    entity: str                # "Client", "Invoice"
    operation: str             # "create", "send", "delete"
    fields: dict[str, Any]     # extracted field values from NL input
    confirmation_required: bool
    confidence: float          # 0.0-1.0 how confident the parser is
    result: Any = None         # filled in by the app after execution

@dataclass
class ActionPlan:
    user_input: str            # the original natural language message
    session_id: str
    steps: list[ActionStep]
    requires_confirmation: bool  # True if any step has confirmation_required
    confirmation_prompt: str   # human-readable summary for user to confirm
```

### `app.handle(text)` - Direct Call Mode

```python
# For apps that manage their own message loop:
plan = await app.handle("create invoice for client James, £500, due next Friday")
# Returns ActionPlan without executing it
# App inspects plan.steps and executes itself
```

### `app.connect()` vs `app.start()`

- `app.connect()` - registers the schema with keprix and returns. App manages its own loop.
- `app.start()` - registers schema + starts an event stream listener that pushes ActionPlans to
  the `@app.on_action` callback. Use this for apps that want fully hands-off operation.

## TypeScript/Node.js SDK Package

### Location

```
keprix/keprix_sdk/typescript/
  package.json          - name: @keprix-ai/sdk, version: 1.0.0
  src/
    index.ts            - exports CarinaApp, Domain, Entity, Field, Operation
    app.ts              - CarinaApp class
    domain.ts           - Domain, Entity, Field, Operation types
    schema.ts           - schema serialiser
    client.ts           - fetch-based HTTP client
    types.ts            - ActionPlan, ActionStep, ExecutionResult interfaces
  README.md
  examples/
    invoice-app.ts
    crm-app.ts
```

Mirror the Python API exactly in TypeScript. Use `async/await` throughout.
No class decorators (no decorator support needed). Use `app.onAction(callback)` instead.

```typescript
import { CarinaApp, Domain, Entity, Field, Operation } from '@keprix-ai/sdk';

const app = new CarinaApp({
  name: 'my-invoicing-app',
  carinaUrl: 'http://localhost:3333',
  apiToken: 'carina_tok_...',
});

app.registerDomain(domain);

app.onAction(async (plan) => {
  for (const step of plan.steps) {
    if (step.entity === 'Invoice' && step.operation === 'send') {
      await emailService.send(step.fields.invoiceId);
      step.result = { status: 'sent' };
    }
  }
  return { success: true, steps: plan.steps };
});

await app.start();
```

## Backend Routes

### Schema Registration

`backend/sdk/routes.py`:

```
POST   /api/sdk/apps/register             - register an app and its domain schema
GET    /api/sdk/apps                      - list registered apps
GET    /api/sdk/apps/{app_id}             - get app + schema
DELETE /api/sdk/apps/{app_id}             - unregister
PUT    /api/sdk/apps/{app_id}/schema      - update schema (hot reload)
```

Registration payload:
```json
{
  "name": "my-invoicing-app",
  "version": "1.0.0",
  "domain": {
    "name": "invoicing",
    "entities": [
      {
        "name": "Invoice",
        "fields": [...],
        "operations": [...]
      }
    ]
  },
  "webhook_url": "http://my-app:8000/carina/actions"  // where to POST ActionPlans
}
```

### Natural Language Execution

```
POST   /api/sdk/execute                   - parse NL input and return ActionPlan
       Body: {
         "app_id": str,
         "message": str,
         "session_id": str?,
         "user_id": str?
       }
       Returns: ActionPlan

POST   /api/sdk/execute/confirm           - user confirmed; trigger webhook delivery
       Body: { "plan_id": str, "confirmed": bool }

GET    /api/sdk/execute/{plan_id}         - get status of a pending plan
```

### Domain-Context Builder

`backend/sdk/domain_context.py`:

This is the core of the SDK backend. When `POST /api/sdk/execute` is called:

1. Load the app's registered schema from DB
2. Build a domain-aware system prompt:
   ```
   You are processing a request for the {app_name} application.
   Available entities: {entity_list}
   Available operations per entity: {operation_map}
   Field definitions and validation rules: {field_specs}
   
   Parse the user's message and return a JSON ActionPlan.
   Extract all mentioned field values. If a required field is missing,
   include it in ActionStep.missing_fields. If the operation is
   destructive (confirmation_required=true), set requires_confirmation=true.
   ```
3. Call the configured LLM with this system prompt + user message
4. Parse the LLM's JSON response into an `ActionPlan`
5. Validate extracted field values against the schema (type checking, enum validation)
6. Return the ActionPlan to the caller

If `confirmation_required` is true in any step, the action plan is stored in
a `pending_sdk_plans` table (TTL: 10 minutes). The app shows the confirmation
prompt to the user, then calls `POST /api/sdk/execute/confirm`.

### Database Schema

```sql
CREATE TABLE sdk_apps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    version TEXT NOT NULL,
    domain_schema JSONB NOT NULL,
    webhook_url TEXT,               -- where to POST ActionPlans
    api_token_id UUID REFERENCES sessions(id),  -- which token registered this app
    is_active BOOLEAN DEFAULT true,
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ
);

CREATE TABLE sdk_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_id UUID REFERENCES sdk_apps(id) ON DELETE CASCADE,
    user_input TEXT NOT NULL,
    session_id TEXT,
    plan JSONB NOT NULL,            -- full ActionPlan JSON
    status TEXT DEFAULT 'pending',  -- 'pending', 'confirmed', 'rejected', 'delivered', 'failed'
    requires_confirmation BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    delivery_response JSONB
);
CREATE INDEX ON sdk_plans (app_id, status, created_at DESC);
```

### Webhook Delivery

When a plan is ready (either no confirmation needed, or user confirmed):
`backend/sdk/delivery.py` - POST the ActionPlan JSON to the app's `webhook_url`.
Retry up to 3 times with exponential backoff on failure.
Record delivery status in `sdk_plans.delivery_response`.

If no `webhook_url` is set, the plan is returned inline from `POST /api/sdk/execute`.
The app polls for the result or uses the SSE stream.

### SSE Stream (alternative to webhook)

`GET /api/sdk/apps/{app_id}/stream` - SSE stream that pushes ActionPlans as they
arrive. Apps that are co-located with keprix can listen here instead of
exposing a webhook endpoint.

## Frontend Pages

Add to `frontend/src/app/(workspace)/sdk/` in Prompt 21's UI work:

`/admin/sdk` - SDK App Manager:
- List registered apps with last-seen timestamp and schema summary
- Register new app form (name, webhook URL)
- Per-app: view schema, view recent plans, revoke

`/admin/sdk/{app_id}/plans` - Plan history:
- List of parsed plans with user input, extracted fields, status
- Re-deliver failed plans

## CLI

```
python -m keprix sdk list              - list registered apps
python -m keprix sdk show {app_id}     - show app schema
python -m keprix sdk unregister {id}   - unregister app
python -m keprix sdk test {app_id}     - interactive: type NL, see parsed ActionPlan
```

`keprix sdk test` is the key developer tool: allows the app developer to type
natural language commands and see exactly what ActionPlan keprix would return,
without triggering the webhook.

## Examples

Write two complete working examples at `keprix_sdk/python/examples/`:

`invoice_app.py`:
- SQLite-backed invoice app
- Registers Client and Invoice entities
- Handles: create client, create invoice, send invoice, mark paid, delete
- Prints a confirmation prompt for destructive operations before calling confirm

`crm_app.py`:
- SQLite-backed CRM app
- Registers Contact, Company, Deal entities
- Handles: create/read/update contact, log note, schedule follow-up

Mirror both examples in `keprix_sdk/typescript/examples/`.

## Acceptance Criteria

- `pip install -e keprix_sdk/python` succeeds
- `python keprix_sdk/python/examples/invoice_app.py` starts without error
- `POST /api/sdk/apps/register` with a valid schema returns `{app_id: "..."}`
- `POST /api/sdk/execute` with `{app_id, message: "create invoice for James £500"}` returns
  ActionPlan with one step: `{entity: "Invoice", operation: "create", fields: {client: "James", amount: 500.00}}`
- `POST /api/sdk/execute` with `{message: "delete all clients"}` returns ActionPlan
  with `requires_confirmation: true`
- `GET /api/sdk/apps/{app_id}/stream` delivers an SSE event when a plan is created
- `/admin/sdk` page renders the app list
- `keprix sdk test {app_id}` parses a typed command and prints the ActionPlan
