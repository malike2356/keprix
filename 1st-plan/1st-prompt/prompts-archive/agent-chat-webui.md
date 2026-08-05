# keprix - Prompt: Agent Chat WebUI

## Purpose

When keprix was forked, the original WebUI was stripped. Users currently interact with keprix through the CLI only. This prompt builds a simple, functional agent chat WebUI so users can interact with keprix from a browser.

It is deliberately minimal: a chat interface, model selector, and session list. Nothing more. The Carina WebUI patterns are adopted directly -- same component structure, same layout, same interaction model. When we are ready to upgrade, we build on this foundation.

## Guiding principle

Adopt, do not invent. Every component, every API call, every layout decision follows the Carina chat WebUI at `carina/03-frontends/client-apps/app.carinaai.uk/src/`. Where keprix has already built equivalent components (ChatWorkspaceShell, ChatInputBar, MessageFeed, CanvasPanel, useChat), use those. Where gaps exist, port the simplest version from Carina.

## What already exists in keprix (do not rebuild)

- `src/app/(workspace)/chat/page.tsx` -- session redirect
- `src/app/(workspace)/chat/[sessionId]/page.tsx` -- chat view shell
- `src/components/chat/CanvasPanel.tsx` -- structured output panel
- `src/components/workspace/ChatWorkspaceShell.tsx` -- workspace shell
- `src/components/workspace/ChatInputBar.tsx` -- message input
- `src/components/workspace/MessageFeed.tsx` -- message list
- `src/hooks/useChat.ts` -- streaming chat hook
- `src/lib/chat-sessions.ts` -- session management
- `src/lib/workspace-api.ts` -- API client

## What to build (adopting Carina patterns)

### 1. Model selector

Port Carina's `ModelSelectorPopover` to keprix.

```
src/components/chat/ModelSelector.tsx
```

- Dropdown or popover listing available LLM providers and models.
- Shows current model with provider icon.
- Fetches models from `GET /api/models`.
- Sets model via `POST /api/sessions/{sessionId}/model`.
- Persists model choice per session.

### 2. Session list sidebar

A left sidebar showing recent sessions, matching Carina's session list pattern.

```
src/components/chat/SessionList.tsx
```

- Lists recent sessions ordered by last activity.
- Each row shows session title (truncated) and relative timestamp.
- Active session is highlighted.
- New chat button at the top.
- Search/filter sessions by title.
- Delete session with confirmation.

### 3. Agent thinking indicator

Show when the agent is thinking, what tool it is using, and intermediate reasoning.

```
src/components/chat/ThinkingBlock.tsx
```

- Collapsible block showing agent reasoning steps.
- Shows tool name and arguments when a tool is being called.
- Shows tool result when it completes.
- Auto-collapses when stream finishes.
- Ported from Carina's `ThinkingBlock`.

### 4. Error and empty states

```
src/components/chat/ChatEmptyState.tsx
src/components/chat/ChatErrorBanner.tsx
```

Empty state when no session is active:
- Welcome message with keprix name and tagline.
- Suggested first prompts.
- Quick-start link to provider setup.

Error banner for API failures:
- Clear error message.
- Retry button.
- Link to diagnostics if error persists.

### 5. Streaming message polish

Refine the existing `MessageFeed` to handle streaming better:

- Smooth text reveal during streaming (no jarring jumps).
- Auto-scroll to bottom on new messages (with a "scroll to bottom" button if user has scrolled up).
- Typing indicator (three dots) before first token arrives.
- Markdown rendering for agent messages (already partially done).
- Copy button on code blocks.
- Timestamp on hover.

### 6. Mobile responsive shell

Ensure the chat works on mobile:

- Sidebar collapses to a hamburger drawer.
- Input bar adapts to mobile keyboard.
- Messages use full width on small screens.
- Canvas panel becomes a full-screen overlay on mobile.

## Files to create or modify

```
src/components/chat/
  ModelSelector.tsx          - NEW: model picker dropdown
  SessionList.tsx            - NEW: sidebar session list
  ThinkingBlock.tsx          - NEW: agent reasoning display
  ChatEmptyState.tsx         - NEW: welcome and prompts
  ChatErrorBanner.tsx        - NEW: error display with retry
  CanvasPanel.tsx            - MODIFY: add mobile overlay mode

src/components/workspace/
  ChatInputBar.tsx           - MODIFY: model selector integration
  MessageFeed.tsx            - MODIFY: smooth streaming, scroll behaviour, markdown
  ChatWorkspaceShell.tsx     - MODIFY: mobile sidebar drawer, session list integration

src/app/(workspace)/chat/
  [sessionId]/page.tsx       - MODIFY: integrate new components
  page.tsx                   - MODIFY: session list on desktop, redirect on mobile

src/hooks/
  useModelSelector.ts        - NEW: model fetch, select, persist
  useSessionList.ts          - NEW: session list fetch, create, delete

src/lib/
  model-api.ts               - NEW: GET /api/models client

tests/frontend/
  test_chat_components.tsx   - render tests for new components
```

## Design constraints

- Use MUI components (already the keprix standard).
- Dark theme by default (matches keprix brand).
- No custom CSS frameworks; stick to MUI `sx` props and the keprix theme.
- All API calls go through `src/lib/` modules (never inline fetch).
- All text is plain ASCII: no em dashes, no en dashes, no emojis in UI copy.

## API endpoints referenced

The WebUI depends on these backend endpoints. If any are missing, build minimal versions:

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/sessions` | GET | List user sessions |
| `/api/sessions` | POST | Create new session |
| `/api/sessions/{id}` | GET | Get session messages |
| `/api/sessions/{id}` | DELETE | Delete session |
| `/api/sessions/{id}/chat` | POST | Send message (SSE stream) |
| `/api/sessions/{id}/model` | POST | Set session model |
| `/api/models` | GET | List available models |

## Acceptance criteria

- User opens keprix in a browser and sees the chat interface.
- User can select a model from the dropdown and send a message.
- Agent response streams in real time with smooth text rendering.
- Thinking steps appear in a collapsible block during agent processing.
- Session list shows recent chats; clicking one loads its messages.
- New chat button creates a fresh session.
- Error states show clear messages with retry actions.
- Interface works on mobile (sidebar drawer, responsive input, full-width messages).
- `pnpm build` passes with no TypeScript errors.
- No Carina brand strings, emojis, em dashes, or placeholder text in UI copy.
