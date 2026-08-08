# Keprix - Prompt 257: Network Egress Policy per Product

## Context

Tool ACL (Prompt 256) controls which tools a product can call. But a tool that is
allowed can still make HTTP requests to any host on the internet. A customer support
agent in Aiva that is allowed to call `web_search.search` should not be able to reach
`169.254.169.254` (AWS metadata), `localhost:5432` (internal Postgres), or
`api.abbis.com` (another product's backend). Nothing currently prevents this.

This prompt enforces per-product network egress: each product declares which external
hosts it is permitted to reach. All outbound HTTP/HTTPS requests from tools in that
product's context are validated against this list. Requests to undeclared hosts are
blocked before the TCP connection is made.

This extends the credential proxy (Prompt 239) with product-scoped routing rules, and
builds on the network isolation work already referenced in
`src/keprix/docs/security/network-egress-isolation.md`.

## What already exists (do not rebuild)

- `security/product_context.py` -- `get_product_context()` from Prompt 255
- `keprix-proxy` from Prompt 239 (extend its route matching with product scope)
- `security/` module -- general security enforcement
- `src/keprix/docs/security/network-egress-isolation.md` -- existing egress doc
  (read before writing any new egress logic)

## Egress policy model

```yaml
# aiva/keprix.yaml
product_id: aiva

network_egress:
  default: deny            # deny all outbound unless explicitly allowed
  allowed_hosts:
    - api.sendgrid.com     # email dispatch
    - api.stripe.com       # payments
    - api.twilio.com       # voice
    - "*.googleapis.com"   # Google APIs (calendar, etc.)
    - api.deepgram.com     # STT
    - api.elevenlabs.io    # TTS
    - api.openai.com       # LLM
    - api.anthropic.com    # LLM
  denied_hosts:
    - 169.254.0.0/16       # Cloud metadata (SSRF protection)
    - 10.0.0.0/8           # Internal RFC1918
    - 172.16.0.0/12        # Internal RFC1918
    - 192.168.0.0/16       # Internal RFC1918
    - localhost
    - 127.0.0.1
    - ::1
```

The `denied_hosts` list is NOT configurable away from the private/loopback ranges.
Those entries are hardcoded minimums. Products can only ADD to `denied_hosts`,
not remove the built-in blocks.

## What to build

### 1. Egress policy registry

`src/keprix/security/egress_policy.py`:

```python
class EgressPolicy:
    """
    Resolves whether a given product is allowed to connect to a given host.
    Loaded from product manifests. Enforced by the EgressGate.
    """

    def __init__(self):
        self._policies: dict[str, ProductEgressRules] = {}
        self._builtin_denied = IPSet([
            "169.254.0.0/16",    # cloud metadata
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "127.0.0.0/8",
            "::1/128",
        ])

    def load_from_manifest(self, manifest: ProductManifest) -> None:
        egress = manifest.network_egress or {}
        self._policies[manifest.product_id] = ProductEgressRules(
            default_deny=egress.get("default", "deny") == "deny",
            allowed_hosts=set(egress.get("allowed_hosts", [])),
            extra_denied_hosts=set(egress.get("denied_hosts", [])),
        )

    def is_allowed(self, product_id: str, host: str, ip: str) -> EgressDecision:
        # Always check builtin denies first (private ranges, loopback)
        if self._is_private(ip):
            return EgressDecision(allowed=False, reason="private_ip_blocked")

        rules = self._policies.get(product_id)
        if rules is None:
            return EgressDecision(allowed=False, reason="unknown_product")

        # Check product's extra denied hosts
        if self._matches_host(host, rules.extra_denied_hosts):
            return EgressDecision(allowed=False, reason="host_denied_by_policy")

        if not rules.default_deny:
            return EgressDecision(allowed=True, reason="default_allow")

        if self._matches_host(host, rules.allowed_hosts):
            return EgressDecision(allowed=True, reason="host_in_allowlist")

        return EgressDecision(allowed=False, reason="host_not_in_allowlist")

    def _matches_host(self, host: str, patterns: set[str]) -> bool:
        """Matches: exact host, wildcard "*.example.com", CIDR for IP patterns."""

    def _is_private(self, ip: str) -> bool:
        """Check if resolved IP is in any private/loopback range."""
```

### 2. Egress gate (HTTP client interceptor)

`src/keprix/security/egress_gate.py`:

The egress gate wraps every HTTP client used by tools. Tools never create bare
`httpx.AsyncClient` or `requests.Session` instances directly; they use the
keprix HTTP client factory, which returns a gate-enforced client.

```python
class EgressGate:
    """
    Wraps httpx.AsyncClient with egress policy enforcement.
    Resolves the destination host/IP before allowing the connection.
    """

    def __init__(self, policy: EgressPolicy):
        self.policy = policy

    def get_client(self) -> httpx.AsyncClient:
        ctx = get_product_context()
        return httpx.AsyncClient(
            transport=EgressGateTransport(self, ctx.product_id)
        )

class EgressGateTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        ip = await self._resolve_ip(host)    # DNS resolution before connection

        decision = self.gate.policy.is_allowed(self.product_id, host, ip)

        if not decision.allowed:
            await egress_audit.log_block(
                product_id=self.product_id,
                host=host,
                ip=ip,
                url=str(request.url),
                reason=decision.reason,
            )
            raise EgressBlocked(
                f"Outbound request to {host} ({ip}) blocked for product "
                f"'{self.product_id}': {decision.reason}. "
                f"Add '{host}' to allowed_hosts in {self.product_id}/keprix.yaml."
            )

        await egress_audit.log_allow(self.product_id, host, ip, str(request.url))
        return await self._transport.handle_async_request(request)
```

### 3. HTTP client factory (replaces bare httpx usage in tools)

`src/keprix/http_client.py`:

```python
def get_http_client(**kwargs) -> httpx.AsyncClient:
    """
    The only way tools should create HTTP clients. Returns a gate-enforced client.
    Raises if called outside a request context (no ProductContext set).
    """
    return egress_gate.get_client(**kwargs)
```

All 60+ tools that currently use `httpx.AsyncClient()` or `requests.get()` directly
must be migrated to use `get_http_client()`. The migration is mechanical: a codemod
replaces the import and constructor call.

Codemod script: `scripts/migrate_http_clients.py`:
```
Find: httpx.AsyncClient(
Replace: get_http_client(

Find: requests.Session()
Replace: (not supported -- migrate to httpx)

Find: requests.get(
Replace: (wrap in async context)
```

### 4. Credential proxy integration

Extend Prompt 239's `proxy.toml` to support per-product route scoping:

```toml
[[routes]]
host = "api.stripe.com"
header_name = "Authorization"
scheme = "Bearer"
secret_ref = "stripe-secret-key"
allowed_products = ["aiva", "abbis"]   # NEW: only these products can use this route

[[routes]]
host = "api.deepgram.com"
header_name = "Authorization"
scheme = "Token"
secret_ref = "deepgram-api-key"
allowed_products = ["aiva"]             # Deepgram only for Aiva (voice)
```

The proxy checks the `X-Keprix-Product` header on incoming requests. If the product is
not in `allowed_products`, the proxy rejects the request before injecting credentials.

This means credential routes are per-product at the proxy level, and egress policy is
per-product at the HTTP client level. Two independent enforcement layers.

### 5. Egress audit log

`src/keprix/security/egress_audit.py`:

Table: `network_egress_log`
```
id, product_id, host, ip, url_path, decision, reason, session_id, tool_name, created_at
```

Dashboard view at `/admin/network-egress`:

| Time | Product | Host | IP | Decision | Reason | Tool |
|------|---------|------|----|----------|--------|------|
| 14:01 | aiva | api.sendgrid.com | 54.x.x.x | ALLOWED | host_in_allowlist | sendgrid.send_email |
| 14:02 | aiva | 192.168.1.1 | 192.168.1.1 | BLOCKED | private_ip_blocked | web_search.search |
| 14:03 | abbis | api.stripe.com | 54.x.x.x | BLOCKED | host_not_in_allowlist | (unknown) |

### 6. Manifest linter extension

Extend `keprix tools acl-lint` (Prompt 256) to also lint `network_egress`:

```
keprix tools acl-lint aiva/keprix.yaml

Network egress:
  OK   api.sendgrid.com       -- reachable (200ms ping)
  OK   api.stripe.com         -- reachable
  WARN *.googleapis.com       -- wildcard; consider listing specific subdomains
  ERR  api.example-gone.com   -- DNS does not resolve; remove or fix
  INFO 3 private ranges blocked by built-in policy (not configurable)
```

## Files to create

```
src/keprix/security/
  egress_policy.py           - EgressPolicy, ProductEgressRules, EgressDecision
  egress_gate.py             - EgressGate, EgressGateTransport, EgressBlocked
  egress_audit.py            - egress audit log writer

src/keprix/
  http_client.py             - get_http_client() factory (gate-enforced)

src/keprix/api/
  egress_audit_routes.py     - GET /api/admin/network-egress (audit table)

scripts/
  migrate_http_clients.py    - codemod: bare httpx -> get_http_client()

frontend/src/app/(admin)/dashboard/
  network-egress/
    page.tsx                 - egress audit trail table

migrations/
  add_network_egress_log_table.py

tests/security/
  test_egress_policy.py
  test_egress_gate.py
  test_egress_audit.py
```

Modifications to existing files:
- All 60+ tools using `httpx.AsyncClient` or `requests.*` -- migrate to `get_http_client()`
- `keprix-proxy/src/config.rs` -- add `allowed_products` field to route configuration
- `keprix-proxy/src/injector.rs` -- check `X-Keprix-Product` header against `allowed_products`
- `extensions/loader.py` -- load `network_egress` from manifest and register with EgressPolicy

## Acceptance criteria

- An Aiva tool call attempting to reach `192.168.1.1` is blocked before DNS resolution
  completes, with a logged `BLOCKED / private_ip_blocked` audit entry.
- A tool in Aiva attempting to reach `api.abbis.com` (not in Aiva's `allowed_hosts`) is
  blocked with a logged `BLOCKED / host_not_in_allowlist` entry.
- A tool in Aiva reaching `api.sendgrid.com` (in allowlist) succeeds normally.
- Wildcard `*.googleapis.com` correctly allows `calendar.googleapis.com` and
  `drive.googleapis.com` but not `evil.googleapis.com.attacker.com`.
- The credential proxy rejects a product not in `allowed_products` for a route even if
  the route host is reachable.
- All 60+ tools pass the codemod migration with no bare `httpx.AsyncClient` instances
  remaining after the migration script runs.
- `keprix tools acl-lint` flags DNS-unreachable hosts in `allowed_hosts`.
- Egress enforcement adds < 2ms overhead per tool HTTP call (DNS is cached after first
  resolution per request).
