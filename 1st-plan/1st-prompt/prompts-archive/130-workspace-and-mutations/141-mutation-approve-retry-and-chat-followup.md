# Keprix - Prompt 141: Mutation Approve, Generic Retry, and Chat Follow-Up

## Context

Read `138-chat-mutation-e2e-wiring-outline.md`.

Complete Prompts **139** and **140** first.

Prompt 136 shipped `MutationCard` with "Installed. Retrying your request..." but
`KeprixRetry` only retries `fetch_stock_price` with a hardcoded ticker regex.
This prompt completes the loop: approve installs the tool and the user sees a
**real** retry result in `/chat`.

Output: `src/keprix/agent/keprix/retry.py`,
`src/keprix/agent/keprix/approval.py`,
`src/keprix/api/conversation_routes.py`,
`frontend/src/hooks/useChat.ts`,
`frontend/src/components/workspace/blocks/MutationCard.tsx`,
`frontend/src/lib/workspace-api.ts`,
`tests/api/test_mutation_approve_retry.py`.

## Step 1: Generic KeprixRetry

Rewrite `src/keprix/agent/keprix/retry.py`:

```python
class KeprixRetry:
    async def retry(
        self,
        *,
        original_message: str,
        tool_name: str,
        session_id: str | None = None,
    ) -> str:
```

Behavior:

1. `registry.get_entry(tool_name)`; if missing return clear error string
2. Build handler input from `original_message` using tool-specific inferencers:
   - `fetch_stock_price`: extract ticker (keep existing behavior)
   - `track_time`: extract project name from quotes or "on {project}" pattern;
     default project `"default"`
   - **Default:** call handler with `{"query": original_message}` or empty dict
     if the skill schema has no required fields
3. Invoke `entry.handler(payload, store=None)` (sync or async per registry)
4. Parse JSON response when possible; format human-readable assistant text
5. Never raise to caller; return error string on exception

Add `tests/mutation/test_retry.py` with mocked registry entries.

## Step 2: Approval workflow returns retry payload

In `approval.py`, after successful install:

```python
retry_message = await KeprixRetry().retry(
    original_message=record.original_task or record.task,
    tool_name=record.tool_name,
    session_id=record.session_id,
)
```

Extend approve response in `conversation_routes.py`:

```python
@router.post("/api/mutations/{record_id}/approve")
async def approve_mutation(...) -> dict[str, Any]:
    ...
    return {
        "record": asdict(record),
        "retry_message": retry_message,
    }
```

Keep backward compatibility: `record` fields remain at top level or nested under
`record` consistently; update `workspace-api.ts` types.

Also update `POST /api/agent/tools/generated/{id}/approve` if it shares the same
workflow (single code path in `ApprovalWorkflow`).

## Step 3: Append retry message to conversation

When approve succeeds from chat, the user should see a new assistant message
without sending again.

**Server option (preferred):**

Add optional query `session_id` to approve endpoint. When present:

1. Append assistant message to workspace session:

```python
{
  "role": "assistant",
  "content": [{"type": "text", "content": retry_message}],
}
```

2. Return `{ record, retry_message, message }` in JSON

**Client option (fallback):**

`MutationCard` calls `onRetryMessage(retry_message)` and `useChat` appends locally.

Implement server persistence so reload shows the retry result.

## Step 4: Frontend wiring

### `workspace-api.ts`

```typescript
export type ApproveMutationResponse = {
  record: GeneratedToolRecord;
  retry_message?: string;
  message?: WorkspaceMessage;
};
```

Update `approveMutation(id, sessionId?)` to pass `session_id` query param.

### `MutationCard.tsx`

After approve:

- If `retry_message` in response, show it below the card (or call parent callback)
- Keep green border + "Installed. Retrying your request..." then replace with
  actual retry text when response arrives

### `useChat.ts`

```typescript
updateMutationStatus(mutationId, status, retryMessage?: string)
```

When `status === "approved"` and `retryMessage`, append or merge assistant text
block (avoid duplicate if server already persisted and client refetches).

### `MessageFeed` / chat page

Pass `sessionId` into `MutationCard` for approve calls.

## Step 5: Chat empty state demo starter (optional but recommended)

File: `frontend/src/components/chat/ChatEmptyState.tsx`

Add starter chip:

```
Track my time on this project
```

Uses same copy as marketing hero terminal demo.

## Step 6: API tests

`tests/api/test_mutation_approve_retry.py`:

1. Create pending mutation record (mock synthesis + sandbox)
2. `POST /api/mutations/{id}/approve?session_id={sid}`
3. Assert tool installed in registry mock
4. Assert `retry_message` non-empty
5. Assert session has new assistant message with retry text
6. Stock price fixture: retry mentions price or structured result
7. Time tracking fixture: retry mentions project or success JSON

## Acceptance Criteria

- Approve from `MutationCard` shows real tool output, not placeholder text
- `KeprixRetry` works for at least `fetch_stock_price` and `track_time`
- Page reload after approve still shows retry assistant message
- `POST /api/mutations/{id}/approve` returns `retry_message`
- Prompt 28 stock-price E2E AC still pass
- `pnpm build` and mutation API tests pass

## Archive Checklist

Move to `prompts-archive/` and update audit + completed README.
