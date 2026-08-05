# Keprix - Prompt 256: Tool Access Control Lists per Product

## Context

Keprix has 60+ tools: terminal execution, file write, database queries, email dispatch,
payment processing, web scraping. Today, any agent running on any product can call any
tool that is registered in the tool registry. A customer support worker in Aiva should
not be able to call `terminal.run`. A property search agent in ABBIS should not be
able to call `stripe.create_payment`. Nothing currently enforces this.

Prompt 240 (Tool Credential Isolation) ensures tools do not hold real secrets.
This prompt ensures tools cannot be called at all unless the running product has
explicitly allowed them. Deny-by-default. Allowlist in the product manifest.

This is the tool layer equivalent of Linux filesystem permissions: the kernel checks
permission before any file operation, regardless of what the calling process thinks
it is doing.

## What already exists (do not rebuild)

- `agent/tool_executor.py` -- tool dispatch (add ACL check here, do not replace)
- `agent/tool_guardrails.py` -- general safety checks (ACL is separate, not a replacement)
- `security/product_context.py` -- `get_product_context()` from Prompt 255
- `extensions/` -- product manifest loading (add `allowed_tools` field here)

## What to build

### 1. Tool ACL in the product manifest

Every product's `keprix.yaml` gains an `allowed_tools` section:

```yaml
# aiva/keprix.yaml
product_id: aiva
name: Aiva

allowed_tools:
  # Explicit allowlist. Any tool not listed here is DENIED for this product.
  # Use "*" to allow all tools in a namespace (not recommended for production).
  - crm.get_contact
  - crm.update_contact
  - crm.create_contact
  - calendar.check_availability
  - calendar.book_appointment
  - sendgrid.send_email
  - web_search.search
  - knowledge.search

  # Tool categories (convenience groupings):
  - category:crm          # all crm.* tools
  - category:calendar     # all calendar.* tools

denied_tools:
  # Explicit denylist. Overrides allowed_tools and categories.
  # Use for "allow category but block one specific dangerous tool."
  - terminal.run
  - terminal.shell
  - file.write
  - file.delete
  - stripe.refund         # finance operations need human approval
```

```yaml
# abbis/keprix.yaml
product_id: abbis
name: ABBIS

allowed_tools:
  - category:crm
  - category:property     # ABBIS-specific domain tools
  - web_search.search
  - document.read
  - document.index
  - calculator.brr        # ABBIS borehole/property calculator

denied_tools:
  - terminal.run
  - file.delete
```

```yaml
# keprix-core (base product, no manifest restriction -- all tools available)
# This is the only product that can call terminal.run, file.write, etc.
# when used directly by the workspace owner through the main UI.
product_id: keprix
allowed_tools: ["*"]
```

### 2. Tool ACL registry

`src/keprix/security/tool_acl.py`:

```python
class ToolACL:
    """
    Resolves whether a given product is allowed to call a given tool.
    Loaded from all registered product manifests at startup.
    Hot-reloaded when a manifest changes (file watcher).
    """

    def __init__(self):
        self._rules: dict[str, ProductToolRules] = {}   # product_id -> rules

    def load_from_manifest(self, manifest: ProductManifest) -> None:
        self._rules[manifest.product_id] = ProductToolRules(
            allowed=set(manifest.allowed_tools or []),
            denied=set(manifest.denied_tools or []),
        )

    def is_allowed(self, product_id: str, tool_name: str) -> ACLDecision:
        """
        Returns: ALLOWED | DENIED | DENIED_NOT_LISTED | UNKNOWN_PRODUCT
        """
        rules = self._rules.get(product_id)
        if rules is None:
            # Unknown product: deny everything
            return ACLDecision.UNKNOWN_PRODUCT

        if product_id == "keprix":
            # Base product: allow everything unless explicitly denied
            if self._matches_any(tool_name, rules.denied):
                return ACLDecision.DENIED
            return ACLDecision.ALLOWED

        # All other products: deny unless explicitly allowed
        if self._matches_any(tool_name, rules.denied):
            return ACLDecision.DENIED
        if self._matches_any(tool_name, rules.allowed):
            return ACLDecision.ALLOWED
        return ACLDecision.DENIED_NOT_LISTED

    def _matches_any(self, tool_name: str, patterns: set[str]) -> bool:
        """
        Matches: exact name, "category:crm" (matches crm.*), "*" (matches all).
        """
        if "*" in patterns:
            return True
        if tool_name in patterns:
            return True
        namespace = tool_name.split(".")[0]
        return f"category:{namespace}" in patterns

@dataclass
class ACLDecision:
    ALLOWED = "allowed"
    DENIED = "denied"                   # explicitly denied
    DENIED_NOT_LISTED = "not_listed"    # not in allowlist
    UNKNOWN_PRODUCT = "unknown_product"
```

### 3. Tool executor enforcement

`src/keprix/agent/tool_executor.py` -- add ACL check before every tool dispatch:

```python
# In _execute_tool_call (called for every tool invocation):
async def _execute_tool_call(self, tool_name: str, arguments: dict) -> Any:
    ctx = get_product_context()
    decision = tool_acl.is_allowed(ctx.product_id, tool_name)

    if decision != ACLDecision.ALLOWED:
        reason = {
            ACLDecision.DENIED:            f"tool '{tool_name}' is explicitly denied for product '{ctx.product_id}'",
            ACLDecision.DENIED_NOT_LISTED: f"tool '{tool_name}' is not in the allowed_tools list for product '{ctx.product_id}'",
            ACLDecision.UNKNOWN_PRODUCT:   f"product '{ctx.product_id}' is not registered",
        }[decision]

        await acl_audit.log_denial(
            product_id=ctx.product_id,
            tool_name=tool_name,
            session_id=ctx.session_id,
            reason=reason,
        )

        raise ToolACLDenied(
            f"Tool call blocked by ACL: {reason}. "
            f"Add '{tool_name}' to allowed_tools in {ctx.product_id}/keprix.yaml to permit."
        )

    # Proceed with normal tool execution
    return await self._dispatch(tool_name, arguments)
```

The `ToolACLDenied` exception returns a structured error to the agent:

```json
{
  "error": "tool_acl_denied",
  "tool": "terminal.run",
  "product": "aiva",
  "message": "Tool call blocked by ACL. Add 'terminal.run' to allowed_tools in aiva/keprix.yaml to permit."
}
```

The agent receives this as a tool result, not an exception, so the conversation can
continue. The agent should tell the user it cannot perform this action.

### 4. ACL audit log

`src/keprix/security/tool_acl_audit.py`:

```python
class ToolACLAudit:
    """Logs every ACL decision: allows and denials."""

    async def log_allow(self, product_id: str, tool_name: str, session_id: str): ...
    async def log_denial(self, product_id: str, tool_name: str,
                         session_id: str, reason: str): ...
```

Table: `tool_acl_log`
```
id, product_id, tool_name, session_id, decision, reason, created_at
```

Dashboard view at `/admin/tool-acl`:

| Time | Product | Tool | Session | Decision | Reason |
|------|---------|------|---------|----------|--------|
| 14:01 | aiva | crm.get_contact | sess_abc | ALLOWED | - |
| 14:02 | aiva | terminal.run | sess_abc | DENIED | explicitly denied |
| 14:03 | abbis | stripe.create_payment | sess_xyz | DENIED_NOT_LISTED | not in allowlist |

### 5. Startup validation

At keprix startup, for each registered product:

```
Tool ACL validation (3 products, 43 tool declarations):
  aiva       -- 12 tools allowed, 4 denied, 0 warnings
  abbis      -- 8 tools allowed, 2 denied, 1 WARNING
    WARNING: abbis allows 'category:crm' but crm.delete_contact is not installed
  petraclus  -- 15 tools allowed, 6 denied, 0 warnings

Run 'keprix tools acl-check' to see the full resolved allowlist per product.
```

CLI command: `keprix tools acl-check [product_id]`
Prints the fully resolved allowed/denied tool list for a product, showing which
pattern matched each tool.

### 6. Developer experience: manifest linter

`src/keprix/cli/acl_lint.py`:

```
keprix tools acl-lint aiva/keprix.yaml

Linting aiva/keprix.yaml:
  OK   crm.get_contact         -- installed
  OK   calendar.book_appointment -- installed
  WARN stripe.refund           -- tool installed but you listed it in denied_tools;
                                  also listed in allowed_tools via 'category:stripe' --
                                  denied_tools takes precedence, this is correct but check intent
  ERR  payments.void_charge    -- tool not installed; remove or install the tool
```

## Files to create

```
src/keprix/security/
  tool_acl.py               - ToolACL registry, ACLDecision, pattern matching
  tool_acl_audit.py         - ACL audit log writer
  tool_acl_denied.py        - ToolACLDenied exception

src/keprix/cli/
  acl_lint.py               - keprix tools acl-lint command
  acl_check.py              - keprix tools acl-check command

src/keprix/api/
  tool_acl_routes.py        - GET /api/admin/tool-acl (audit table)

frontend/src/app/(admin)/dashboard/
  tool-acl/
    page.tsx                - ACL audit trail table

migrations/
  add_tool_acl_log_table.py

tests/security/
  test_tool_acl.py
  test_tool_acl_audit.py
  test_acl_lint.py
```

Modifications to existing files:
- `agent/tool_executor.py` -- add ACL check before every dispatch
- `extensions/loader.py` -- load `allowed_tools` / `denied_tools` from manifest and
  register with ToolACL
- `keprix.yaml` (all registered products) -- add `allowed_tools` and `denied_tools`

## Acceptance criteria

- A keprix agent running as product `aiva` cannot call `terminal.run`. The attempt
  returns a structured `tool_acl_denied` error, not an exception.
- A product with an empty or missing `allowed_tools` field is denied all tools.
- `category:crm` in `allowed_tools` grants access to all `crm.*` tools.
- A tool in `denied_tools` is blocked even if it also matches an `allowed_tools` pattern.
- Every ACL decision (allow and deny) is logged to `tool_acl_log`.
- `keprix tools acl-check aiva` prints the complete resolved tool list for aiva.
- `keprix tools acl-lint aiva/keprix.yaml` flags tools not installed and patterns that
  conflict.
- Startup validation warns on missing tools in the allowlist but does not block startup.
- Startup validation does block startup if a product has no manifest and product_id
  is not `keprix`.
- ACL check adds < 0.5ms overhead per tool call (hash lookup, not a DB query).
