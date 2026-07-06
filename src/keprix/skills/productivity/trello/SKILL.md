---
name: trello
description: Trello REST API via curl. Boards, lists, cards CRUD.
version: 1.0.0
author: community
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [TRELLO_API_KEY, TRELLO_TOKEN]
  commands: [curl]
metadata:
  keprix:
    tags: [Trello, Productivity, Kanban, API, Project Management]
    homepage: https://developer.atlassian.com/cloud/trello/rest/
    related_skills: [notion, productivity-integrations, project-tracking]
---

# Trello; Boards, Lists & Cards

Work with Trello's REST API directly via `curl` using the `terminal` tool. No MCP server, no OAuth browser flow in chat; just `curl` with an API key and token.

## Prerequisites

1. Open the Trello Power-Up admin page: https://trello.com/power-ups/admin
2. Click **New** (or open an existing Power-Up) and copy the **API key**.
3. Generate a **token** for your account (the admin page links to token generation; approve read/write scopes your workflow needs).
4. Store both values in `${KEPRIX_HOME:-~/.keprix}/.env` (or via `keprix setup`):
   ```
   TRELLO_API_KEY=your_api_key_here
   TRELLO_TOKEN=your_token_here
   ```
5. **Board access:** tokens are tied to the member who generated them. Private boards must belong to that member (or the token must have been granted access).

> Note: Trello uses key + token query parameters on every request, not a Bearer header.

## API Basics

- **Endpoint:** `https://api.trello.com/1`
- **Auth:** append `?key=$TRELLO_API_KEY&token=$TRELLO_TOKEN` to every URL (or `&key=...&token=...` when other query params exist).
- **Content type:** `application/json` for POST/PUT bodies.
- **Object IDs:** boards, lists, and cards use 24-character hex strings (e.g. `5f1a2b3c4d5e6f7a8b9c0d1e`).

Base curl pattern:
```bash
curl -s "https://api.trello.com/1/members/me/boards?key=$TRELLO_API_KEY&token=$TRELLO_TOKEN" \
  | python3 -m json.tool
```

Use `-s` on every call so progress bars do not pollute agent output.

## Common Queries

### List boards for the authenticated member
```bash
curl -s "https://api.trello.com/1/members/me/boards?fields=name,url,closed&key=$TRELLO_API_KEY&token=$TRELLO_TOKEN" \
  | python3 -m json.tool
```

### List lists on a board
```bash
BOARD_ID=replace_me
curl -s "https://api.trello.com/1/boards/$BOARD_ID/lists?fields=name,closed&key=$TRELLO_API_KEY&token=$TRELLO_TOKEN" \
  | python3 -m json.tool
```

### List cards in a list
```bash
LIST_ID=replace_me
curl -s "https://api.trello.com/1/lists/$LIST_ID/cards?fields=name,due,closed,url&key=$TRELLO_API_KEY&token=$TRELLO_TOKEN" \
  | python3 -m json.tool
```

### Open cards on a board (all lists)
```bash
BOARD_ID=replace_me
curl -s "https://api.trello.com/1/boards/$BOARD_ID/cards?filter=open&fields=name,idList,due,url&key=$TRELLO_API_KEY&token=$TRELLO_TOKEN" \
  | python3 -m json.tool
```

## Create and Update Cards

### Create a card
```bash
LIST_ID=replace_me
curl -s -X POST "https://api.trello.com/1/cards?key=$TRELLO_API_KEY&token=$TRELLO_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"Review Q3 roadmap\", \"idList\": \"$LIST_ID\"}" \
  | python3 -m json.tool
```

### Move a card to another list
```bash
CARD_ID=replace_me
NEW_LIST_ID=replace_me
curl -s -X PUT "https://api.trello.com/1/cards/$CARD_ID?key=$TRELLO_API_KEY&token=$TRELLO_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"idList\": \"$NEW_LIST_ID\"}" \
  | python3 -m json.tool
```

### Set or clear a due date (ISO 8601)
```bash
CARD_ID=replace_me
curl -s -X PUT "https://api.trello.com/1/cards/$CARD_ID?key=$TRELLO_API_KEY&token=$TRELLO_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"due\": \"2026-07-15T17:00:00.000Z\"}" \
  | python3 -m json.tool
```

### Archive a card
```bash
CARD_ID=replace_me
curl -s -X PUT "https://api.trello.com/1/cards/$CARD_ID?closed=true&key=$TRELLO_API_KEY&token=$TRELLO_TOKEN" \
  | python3 -m json.tool
```

## Rate Limits and Errors

- Trello enforces per-key rate limits (typically **300 requests per 10 seconds** per API key; burst behavior may vary). On `429`, read the `Retry-After` header when present and back off exponentially (start at 1s, max 3 retries).
- Common HTTP codes:
  - `401`: invalid key or token; regenerate the token or fix `.env`.
  - `404`: wrong ID or the token cannot see that board/list/card.
  - `429`: rate limited; slow down and retry.
- Parse error bodies with `python3 -m json.tool`; Trello returns a plain-text or JSON message describing the failure.

## Typical Keprix Workflow

1. **Confirm auth.** `GET /1/members/me` with key and token; expect HTTP 200 and a `username` field.
2. **Resolve board ID.** List boards or ask the user for the board URL (ID is the third path segment).
3. **Read before write.** List open cards with `filter=open` before creating duplicates.
4. **Batch carefully.** There is no bulk card create endpoint; stay under rate limits when syncing many cards.
5. **Destructive ops.** Archiving and moving cards are reversible in the UI but should be confirmed when the user asked for a dry run.

## When to Use This Skill vs MCP

| Situation | Prefer |
| --- | --- |
| `mcp_trello_*` tools are available (server added at `/admin/mcp`) | **MCP tools**; structured tool calls, no manual curl |
| One-off list/move/create in a session without MCP installed | **This skill** via `terminal` + `curl` |
| User needs guided OAuth or catalog install | Send them to `/admin/mcp` to add the Trello MCP server |
| Cross-app routing (Notion vs Trello vs RAG) | Load the **`productivity-integrations`** skill |

MCP tool names follow the pattern `mcp_trello_<tool_name>` when the server is registered as `trello` in `config.yaml`.

## Important Notes for Keprix

- **Always use the `terminal` tool with `curl`.** Do not use `web_extract` (no auth query params) or browser automation for API work.
- **`TRELLO_API_KEY` and `TRELLO_TOKEN` flow from `${KEPRIX_HOME:-~/.keprix}/.env`** into subprocesses when this skill is loaded.
- **URL-encode card names** only when passing them as query parameters; JSON bodies handle special characters safely.
- **Pretty-print with `python3 -m json.tool`** rather than assuming `jq` is installed.
- See `references/rest-endpoints.md` in this skill folder for a concise endpoint table.
