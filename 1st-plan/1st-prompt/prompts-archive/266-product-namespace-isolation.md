# Keprix - Prompt 255: Product Namespace Isolation

## Context

Keprix makes an "agent OS" claim. A real OS guarantees that process A cannot read
process B's memory. Keprix currently does not guarantee this. Aiva, ABBIS, and Petraclus
running on the same keprix instance share the same data plane. A session in Aiva can, in
theory, retrieve a memory that was written by ABBIS. An API route that checks
`workspace_id` in some queries but not others is not an isolation boundary -- it is a
convention.

This prompt hardens the data plane so product namespace isolation is structural and
enforced at every layer, not reliant on developer convention. No query should be able to
return data from a namespace it did not authenticate into. No exception.

## What already exists (do not rebuild)

- `data_architecture/data_plane.py` -- workspace-scoped data plane (extend, do not replace)
- `data_architecture/schemas.py` -- `CanonicalIds` with `workspace_id`, `tenant_id`
- `api/conversation_routes.py`, `api/admin_workspace_routes.py` -- existing route patterns
- `security/sessions.py` -- session auth (extend to carry product context)
- `extensions/` -- extension discovery (read product_id from keprix.yaml here)

## Isolation model

```
Tenant
  └── Product (Aiva | ABBIS | Petraclus | keprix-core)
        └── Workspace
              └── Resources (sessions, memories, skills, tasks, documents)
```

Rules:
- A request authenticated as product `aiva` can only access resources where
  `product_id = 'aiva'`.
- A request authenticated as workspace `ws_abc` can only access resources where
  `workspace_id = 'ws_abc'`.
- `keprix-core` (the base keprix product) has no product_id restriction -- it sees all
  its own resources but not product-scoped ones unless explicitly granted.
- Cross-product access is never implicit. It requires an explicit grant (Prompt 259
  defines the grant model).
- The rules are enforced in middleware, not in individual route handlers. A route handler
  that forgets to filter by workspace_id is protected by the middleware.

## What to build

### 1. Product context in every request

`src/keprix/security/product_context.py`:

```python
@dataclass(frozen=True)
class ProductContext:
    product_id: str          # "aiva" | "abbis" | "petraclus" | "keprix"
    workspace_id: str
    tenant_id: str | None
    session_id: str | None
    scopes: frozenset[str]   # capabilities granted to this product in this request

_PRODUCT_CONTEXT: contextvars.ContextVar[ProductContext] = \
    contextvars.ContextVar("product_context")

def get_product_context() -> ProductContext:
    ctx = _PRODUCT_CONTEXT.get(None)
    if ctx is None:
        raise RuntimeError("No product context set. Request not going through auth middleware.")
    return ctx

def set_product_context(ctx: ProductContext) -> Token:
    return _PRODUCT_CONTEXT.set(ctx)
```

The `product_id` is resolved at auth time from:
1. The `X-Keprix-Product` request header (set by the extension gateway)
2. The JWT claim `product_id` (if using token auth)
3. The API key's registered product (if using key auth)
4. Fallback: `keprix` (base product, restricted to core resources)

### 2. Isolation middleware

`src/keprix/security/isolation_middleware.py`:

```python
class IsolationMiddleware:
    """
    FastAPI middleware that sets ProductContext on every request and
    registers a query interceptor that enforces namespace isolation.
    """

    async def __call__(self, request: Request, call_next):
        product_id = self._resolve_product_id(request)
        workspace_id = self._resolve_workspace_id(request)

        ctx = ProductContext(
            product_id=product_id,
            workspace_id=workspace_id,
            tenant_id=self._resolve_tenant_id(request),
            session_id=request.headers.get("X-Keprix-Session"),
            scopes=self._resolve_scopes(request),
        )
        token = set_product_context(ctx)

        # Register the query filter for this request
        IsolationQueryFilter.activate(ctx)

        try:
            response = await call_next(request)
        finally:
            _PRODUCT_CONTEXT.reset(token)
            IsolationQueryFilter.deactivate()

        return response
```

### 3. Query filter (row-level security at the ORM layer)

`src/keprix/security/isolation_query_filter.py`:

```python
class IsolationQueryFilter:
    """
    Intercepts SQLAlchemy queries and appends workspace_id + product_id
    WHERE clauses automatically. No route handler needs to remember.
    """

    ISOLATED_TABLES = {
        "memories",
        "skills",
        "tasks",
        "sessions",
        "session_messages",
        "documents",
        "retrieval_graph_edges",
        "playbook_runs",
        "tool_audit_log",
        "brain_share_links",
    }

    @classmethod
    def activate(cls, ctx: ProductContext):
        """Register SQLAlchemy query event listener for this request context."""
        event.listen(Session, "before_compile", cls._apply_filter, propagate=True)

    @classmethod
    def _apply_filter(cls, orm_query):
        """Append workspace_id filter to any query touching isolated tables."""
        ctx = get_product_context()
        for entity in orm_query.column_descriptions:
            table = getattr(entity.get("entity"), "__tablename__", None)
            if table in cls.ISOLATED_TABLES:
                orm_query = orm_query.filter(
                    entity["entity"].workspace_id == ctx.workspace_id
                )
                # If the table has product_id, enforce that too
                if hasattr(entity["entity"], "product_id"):
                    orm_query = orm_query.filter(
                        entity["entity"].product_id == ctx.product_id
                    )
        return orm_query
```

For raw SQL queries (used in `data_architecture/`):

```python
class IsolatedDataPlane:
    """
    Wrapper around the workspace data plane that injects isolation context
    into every raw SQL query. Prevents queries that omit workspace_id.
    """

    def execute(self, sql: str, params: list) -> list:
        ctx = get_product_context()
        if "WHERE" not in sql.upper() and any(
            table in sql for table in IsolationQueryFilter.ISOLATED_TABLES
        ):
            raise IsolationViolation(
                f"Raw query on isolated table without WHERE clause: {sql[:100]}"
            )
        # Validate that workspace_id is in params if referenced in SQL
        if ":workspace_id" in sql and ctx.workspace_id not in str(params):
            raise IsolationViolation("workspace_id param missing or mismatched")
        return self._plane.execute(sql, params)
```

### 4. Schema migration: add product_id to isolated tables

`migrations/add_product_id_to_isolated_tables.py`:

```python
# Add product_id column to all isolated tables.
# Default value: 'keprix' (all existing data belongs to the base product).
# Backfill: use the workspace's registered product_id if set, else 'keprix'.
# Add composite index on (workspace_id, product_id) for all isolated tables.

ISOLATED_TABLES = [
    "memories", "skills", "tasks", "sessions",
    "session_messages", "documents", "retrieval_graph_edges",
]

def upgrade():
    for table in ISOLATED_TABLES:
        op.add_column(table, sa.Column("product_id", sa.String, nullable=False, server_default="keprix"))
        op.create_index(f"ix_{table}_isolation", table, ["workspace_id", "product_id"])
```

### 5. Isolation violation handler

When a query would return data outside the product's namespace:

```python
class IsolationViolation(Exception):
    """Raised when a query attempts to access data outside its product namespace."""

# In the middleware, convert IsolationViolation to HTTP 403:
@app.exception_handler(IsolationViolation)
async def isolation_violation_handler(request, exc):
    logger.critical(
        "ISOLATION VIOLATION: product=%s workspace=%s path=%s",
        get_product_context().product_id,
        get_product_context().workspace_id,
        request.url.path,
    )
    # Also emit a Scout alert (if Scout is running)
    await scout_client.alert("isolation_violation", severity="critical", detail=str(exc))
    return JSONResponse(status_code=403, content={"error": "Access denied"})
```

### 6. Explicit cross-product grant (for legitimate shared data)

Some data is intentionally shared (e.g., a document uploaded by the workspace owner and
accessible to all products). This uses an explicit grant, not a namespace exception:

```python
class CrossProductGrant:
    """
    Allows product B to read a specific resource owned by product A.
    Stored in the database. Audited on every access.
    """
    grant_id: str
    grantor_product_id: str
    grantee_product_id: str
    resource_kind: str        # "document" | "memory" | "skill"
    resource_id: str
    workspace_id: str
    granted_by: str           # user_id who created the grant
    granted_at: datetime
    expires_at: datetime | None
    scopes: list[str]         # ["read"] -- never ["write"] for cross-product
```

## Files to create

```
src/keprix/security/
  product_context.py          - ProductContext dataclass, contextvars accessor
  isolation_middleware.py     - FastAPI middleware setting context on every request
  isolation_query_filter.py   - SQLAlchemy listener + IsolatedDataPlane wrapper
  isolation_violation.py      - IsolationViolation exception and handler
  cross_product_grant.py      - CrossProductGrant model and enforcement

src/keprix/database/
  (extend existing models)    - add product_id column to isolated tables

migrations/
  add_product_id_to_isolated_tables.py

tests/security/
  test_product_context.py
  test_isolation_middleware.py
  test_isolation_query_filter.py
  test_isolation_violation.py
  test_cross_product_grant.py
```

## Acceptance criteria

- A request authenticated as product `aiva` cannot retrieve memories written by product
  `abbis`, even if both use the same `workspace_id`.
- A raw SQL query on an isolated table without a `WHERE workspace_id = ?` clause raises
  `IsolationViolation` rather than returning data.
- The schema migration adds `product_id` to all isolated tables with a default of
  `keprix` for existing rows.
- An `IsolationViolation` returns HTTP 403 and logs a CRITICAL-level event.
- A `CrossProductGrant` with `scopes=["read"]` allows grantee product to read the
  specific resource and nothing else.
- Isolation enforcement adds < 1ms overhead to the median API request.
- Running the full test suite with the middleware active shows zero unintended
  cross-product data leaks across all existing API routes.
