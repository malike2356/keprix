# Keprix Prompt 136: Agent Conversation Workspace

**Status:** Completed 2026-07-06. Evidence: `MessageFeed.tsx`, `useChat.ts`, `MutationCard.tsx`, `ChatWorkspaceShell.tsx`.

## Purpose

Build a complete, production-quality agent conversation UI. The user types a message, the agent
streams a response, tool calls are rendered inline as collapsible blocks, mutation approval prompts
appear in-stream when the agent synthesises a new tool, and the session list sidebar lets the user
switch between conversations.

The full component tree is already scaffolded. This prompt makes every component functional.

---

## Dependencies

- `frontend/src/app/(workspace)/chat/page.tsx` (exists - new chat landing)
- `frontend/src/app/(workspace)/chat/[sessionId]/page.tsx` (exists - active session)
- `frontend/src/components/workspace/ChatWorkspaceShell.tsx` (exists - sidebar + header)
- `frontend/src/components/workspace/MessageFeed.tsx` (exists - scaffold)
- `frontend/src/components/workspace/ChatInputBar.tsx` (exists - scaffold)
- `frontend/src/components/chat/SessionList.tsx` (exists - scaffold)
- `frontend/src/components/chat/ChatEmptyState.tsx` (exists - starter prompts)
- `frontend/src/components/chat/KeprixWordmark.tsx` (exists)
- `frontend/src/components/chat/ChatStatusBar.tsx` (exists - scaffold)
- `frontend/src/components/chat/ChatErrorBanner.tsx` (exists - scaffold)
- `frontend/src/components/chat/ThinkingBlock.tsx` (exists - scaffold)
- `frontend/src/components/chat/CanvasPanel.tsx` (exists - scaffold)
- `frontend/src/hooks/useChat.ts` (exists - streaming hook)
- `frontend/src/hooks/useStartNewConversation.ts` (exists)
- `frontend/src/lib/workspace-api.ts` (exists - all fetch functions scaffolded)
- Backend: `POST /api/workspace/conversations`, `GET /api/workspace/conversations/{id}`,
  `GET /api/workspace/conversations`, `POST /api/workspace/conversations/{id}/messages` (SSE),
  `GET /api/workspace/models`
- Prompt 116 complete (theme)

---

## What to build

### 1. MessageFeed

**`frontend/src/components/workspace/MessageFeed.tsx`** (EDIT)

The core rendering surface. Each message in `messages: Message[]` is rendered as a distinct card.

Message types to handle:
- `role: "user"` - right-aligned bubble, user initials avatar
- `role: "assistant"` - left-aligned, no avatar, Keprix logo or dot
- `role: "system"` - centered muted pill (e.g. "Model switched to claude-3-5-sonnet")
- `role: "tool_result"` - collapsible code block

```tsx
"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Avatar from "@mui/material/Avatar";
import Collapse from "@mui/material/Collapse";
import { alpha } from "@mui/material/styles";
import { KEPRIX_COLORS } from "@/theme/keprix-theme";
import type { Message } from "@/hooks/useChat";
import ToolCallBlock from "@/components/workspace/ToolCallBlock";
import MutationApprovalBlock from "@/components/workspace/MutationApprovalBlock";
import MarkdownRenderer from "@/components/workspace/MarkdownRenderer";

type MessageFeedProps = {
  messages: Message[];
  userInitials: string;
  onMutationStatusChange?: (toolCallId: string, status: "approved" | "rejected") => void;
};

export default function MessageFeed({
  messages,
  userInitials,
  onMutationStatusChange,
}: MessageFeedProps) {
  const bottomRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2, py: 2, px: { xs: 2, md: 3 } }}>
      {messages.map((msg) => (
        <MessageBubble
          key={msg.id}
          message={msg}
          userInitials={userInitials}
          onMutationStatusChange={onMutationStatusChange}
        />
      ))}
      <div ref={bottomRef} />
    </Box>
  );
}
```

### 2. MessageBubble

**`frontend/src/components/workspace/MessageBubble.tsx`** (NEW)

Single message renderer. Handles user/assistant/system/tool_result roles.

```tsx
"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Avatar from "@mui/material/Avatar";
import { alpha } from "@mui/material/styles";
import { KEPRIX_COLORS } from "@/theme/keprix-theme";
import type { Message } from "@/hooks/useChat";
import ToolCallBlock from "@/components/workspace/ToolCallBlock";
import MutationApprovalBlock from "@/components/workspace/MutationApprovalBlock";
import MarkdownRenderer from "@/components/workspace/MarkdownRenderer";

export default function MessageBubble({
  message,
  userInitials,
  onMutationStatusChange,
}: {
  message: Message;
  userInitials: string;
  onMutationStatusChange?: (toolCallId: string, status: "approved" | "rejected") => void;
}) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  if (isSystem) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center" }}>
        <Typography
          variant="caption"
          sx={{
            px: 2,
            py: 0.5,
            bgcolor: alpha(KEPRIX_COLORS.divider, 0.5),
            borderRadius: 999,
            color: "text.secondary",
          }}
        >
          {message.content as string}
        </Typography>
      </Box>
    );
  }

  // Check if message has tool calls embedded in content
  const hasMutationApproval =
    !isUser && typeof message.content === "object" && message.content !== null &&
    "mutation_approval" in (message.content as object);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: isUser ? "row-reverse" : "row",
        gap: 1.5,
        alignItems: "flex-start",
        maxWidth: "100%",
      }}
    >
      {isUser ? (
        <Avatar
          sx={{
            width: 32,
            height: 32,
            bgcolor: "primary.main",
            fontSize: "0.75rem",
            fontWeight: 700,
            flexShrink: 0,
          }}
        >
          {userInitials}
        </Avatar>
      ) : (
        <Box
          sx={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            bgcolor: alpha(KEPRIX_COLORS.primary, 0.15),
            border: `1px solid ${alpha(KEPRIX_COLORS.primary, 0.3)}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <Typography sx={{ fontSize: "0.65rem", fontWeight: 700, color: KEPRIX_COLORS.primary }}>
            KP
          </Typography>
        </Box>
      )}

      <Box
        sx={{
          maxWidth: { xs: "88%", md: "75%" },
          bgcolor: isUser ? "primary.main" : "background.paper",
          color: isUser ? "primary.contrastText" : "text.primary",
          px: 2,
          py: 1.5,
          borderRadius: isUser ? "18px 18px 4px 18px" : "4px 18px 18px 18px",
          border: isUser ? "none" : `1px solid ${alpha(KEPRIX_COLORS.divider, 0.6)}`,
          boxShadow: 1,
        }}
      >
        {hasMutationApproval ? (
          <MutationApprovalBlock
            message={message}
            onStatusChange={onMutationStatusChange}
          />
        ) : message.tool_calls && message.tool_calls.length > 0 ? (
          <>
            <MarkdownRenderer content={typeof message.content === "string" ? message.content : ""} />
            {message.tool_calls.map((tc) => (
              <ToolCallBlock key={tc.id} toolCall={tc} />
            ))}
          </>
        ) : (
          <MarkdownRenderer content={typeof message.content === "string" ? message.content : ""} />
        )}
      </Box>
    </Box>
  );
}
```

### 3. MarkdownRenderer

**`frontend/src/components/workspace/MarkdownRenderer.tsx`** (NEW or EDIT if scaffolded)

Render assistant message body as Markdown. Use `react-markdown` (add to package.json if absent,
or use `@uiw/react-markdown-preview` which may already be installed). Code blocks must be
syntax highlighted.

```tsx
"use client";

import * as React from "react";
import Box from "@mui/material/Box";

type MarkdownRendererProps = {
  content: string;
};

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  // If react-markdown is not installed, render as pre-formatted text for now:
  return (
    <Box
      sx={{
        "& p": { m: 0, mb: 0.75, lineHeight: 1.7 },
        "& p:last-child": { mb: 0 },
        "& code": {
          fontFamily: "monospace",
          fontSize: "0.82em",
          bgcolor: "rgba(0,0,0,0.15)",
          px: 0.5,
          py: 0.25,
          borderRadius: 0.5,
        },
        "& pre": {
          bgcolor: "rgba(0,0,0,0.25)",
          p: 1.5,
          borderRadius: 1,
          overflow: "auto",
          fontSize: "0.82em",
          fontFamily: "monospace",
        },
        "& ul, & ol": { pl: 2.5, mb: 0.75 },
        "& li": { mb: 0.25 },
        "& a": { color: "primary.light" },
      }}
    >
      <span style={{ whiteSpace: "pre-wrap" }}>{content}</span>
    </Box>
  );
}

// TODO: Replace with react-markdown for proper rendering:
// import ReactMarkdown from "react-markdown";
// import remarkGfm from "remark-gfm";
// return <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>;
```

### 4. ToolCallBlock

**`frontend/src/components/workspace/ToolCallBlock.tsx`** (NEW)

Collapsible block showing a tool invocation. Collapsed by default (shows tool name + status icon).
Expanded: shows input JSON and output.

```tsx
"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import BuildCircleIcon from "@mui/icons-material/BuildCircle";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import { alpha } from "@mui/material/styles";
import { KEPRIX_COLORS } from "@/theme/keprix-theme";

export type ToolCallData = {
  id: string;
  name: string;
  input?: unknown;
  output?: unknown;
  status?: "running" | "success" | "error";
  error?: string;
};

export default function ToolCallBlock({ toolCall }: { toolCall: ToolCallData }) {
  const [open, setOpen] = React.useState(false);
  const statusIcon =
    toolCall.status === "success" ? (
      <CheckCircleOutlineIcon fontSize="small" sx={{ color: "success.main" }} />
    ) : toolCall.status === "error" ? (
      <ErrorOutlineIcon fontSize="small" sx={{ color: "error.main" }} />
    ) : (
      <HourglassEmptyIcon fontSize="small" sx={{ color: "text.secondary", animation: "spin 1s linear infinite" }} />
    );

  return (
    <Box
      sx={{
        mt: 1,
        border: `1px solid ${alpha(KEPRIX_COLORS.divider, 0.7)}`,
        borderRadius: 1.5,
        overflow: "hidden",
        bgcolor: alpha("#000", 0.15),
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          px: 1.5,
          py: 0.75,
          cursor: "pointer",
          "&:hover": { bgcolor: alpha("#fff", 0.04) },
        }}
        onClick={() => setOpen((v) => !v)}
      >
        <BuildCircleIcon fontSize="small" sx={{ color: KEPRIX_COLORS.secondary, flexShrink: 0 }} />
        <Typography variant="caption" sx={{ fontFamily: "monospace", flex: 1, color: "text.primary", fontWeight: 600 }}>
          {toolCall.name}
        </Typography>
        {statusIcon}
        <IconButton
          size="small"
          sx={{ transform: open ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}
          aria-label={open ? "Collapse tool call" : "Expand tool call"}
        >
          <ExpandMoreIcon fontSize="small" />
        </IconButton>
      </Box>
      <Collapse in={open}>
        <Box sx={{ px: 1.5, pb: 1.5 }}>
          {toolCall.input !== undefined && (
            <>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: "block", mb: 0.5 }}>
                Input
              </Typography>
              <Box
                component="pre"
                sx={{
                  m: 0,
                  p: 1,
                  borderRadius: 1,
                  bgcolor: alpha("#000", 0.3),
                  fontSize: "0.75rem",
                  fontFamily: "monospace",
                  overflow: "auto",
                  maxHeight: 200,
                  color: "text.primary",
                }}
              >
                {JSON.stringify(toolCall.input, null, 2)}
              </Box>
            </>
          )}
          {toolCall.output !== undefined && (
            <>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ fontWeight: 600, display: "block", mb: 0.5, mt: toolCall.input !== undefined ? 1 : 0 }}
              >
                Output
              </Typography>
              <Box
                component="pre"
                sx={{
                  m: 0,
                  p: 1,
                  borderRadius: 1,
                  bgcolor: alpha("#000", 0.3),
                  fontSize: "0.75rem",
                  fontFamily: "monospace",
                  overflow: "auto",
                  maxHeight: 200,
                  color: "text.primary",
                }}
              >
                {typeof toolCall.output === "string"
                  ? toolCall.output
                  : JSON.stringify(toolCall.output, null, 2)}
              </Box>
            </>
          )}
          {toolCall.error && (
            <Typography variant="caption" color="error.main" sx={{ display: "block", mt: 0.5 }}>
              Error: {toolCall.error}
            </Typography>
          )}
        </Box>
      </Collapse>
    </Box>
  );
}
```

### 5. MutationApprovalBlock

**`frontend/src/components/workspace/MutationApprovalBlock.tsx`** (NEW)

When the Mutation Engine stages a new tool, the assistant message contains a structured approval
block. Render it as a diff card with Approve and Reject buttons.

The backend sends a message with `mutation_status: "staged"` and a tool diff in the content.
The `updateMutationStatus(toolCallId, status)` from `useChat` sends the decision back.

```tsx
"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import { alpha } from "@mui/material/styles";
import { KEPRIX_COLORS } from "@/theme/keprix-theme";
import type { Message } from "@/hooks/useChat";

type MutationApprovalBlockProps = {
  message: Message;
  onStatusChange?: (toolCallId: string, status: "approved" | "rejected") => void;
};

export default function MutationApprovalBlock({ message, onStatusChange }: MutationApprovalBlockProps) {
  const content = message.content as Record<string, unknown>;
  const toolName = String(content.tool_name ?? "New tool");
  const diff = String(content.diff ?? "");
  const linesOfCode = Number(content.lines_of_code ?? 0);
  const currentStatus = String(content.mutation_status ?? "staged");
  const toolCallId = String(content.tool_call_id ?? message.id);

  const isPending = currentStatus === "staged";

  return (
    <Box
      sx={{
        border: `1px solid ${alpha(KEPRIX_COLORS.secondary, 0.4)}`,
        borderRadius: 2,
        overflow: "hidden",
        bgcolor: alpha(KEPRIX_COLORS.secondary, 0.05),
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          px: 2,
          py: 1.25,
          bgcolor: alpha(KEPRIX_COLORS.secondary, 0.08),
          borderBottom: `1px solid ${alpha(KEPRIX_COLORS.secondary, 0.2)}`,
        }}
      >
        <AutoFixHighIcon sx={{ color: KEPRIX_COLORS.secondary, fontSize: 20 }} />
        <Box sx={{ flex: 1 }}>
          <Typography variant="body2" sx={{ fontWeight: 700 }}>
            Mutation Engine: new tool synthesised
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {toolName} - {linesOfCode} lines
          </Typography>
        </Box>
        <Chip
          label={currentStatus}
          size="small"
          color={
            currentStatus === "approved"
              ? "success"
              : currentStatus === "rejected"
              ? "error"
              : "warning"
          }
          variant="outlined"
        />
      </Box>

      {diff && (
        <Box
          component="pre"
          sx={{
            m: 0,
            px: 2,
            py: 1.5,
            fontSize: "0.76rem",
            fontFamily: "monospace",
            overflow: "auto",
            maxHeight: 280,
            color: "text.primary",
            lineHeight: 1.6,
            "& .diff-add": { color: "success.main" },
            "& .diff-del": { color: "error.main" },
          }}
        >
          {diff}
        </Box>
      )}

      {isPending && onStatusChange ? (
        <Box
          sx={{
            display: "flex",
            gap: 1.5,
            px: 2,
            py: 1.25,
            borderTop: `1px solid ${alpha(KEPRIX_COLORS.secondary, 0.2)}`,
          }}
        >
          <Button
            size="small"
            variant="contained"
            color="success"
            startIcon={<CheckIcon />}
            onClick={() => onStatusChange(toolCallId, "approved")}
          >
            Approve
          </Button>
          <Button
            size="small"
            variant="outlined"
            color="error"
            startIcon={<CloseIcon />}
            onClick={() => onStatusChange(toolCallId, "rejected")}
          >
            Reject
          </Button>
          <Typography variant="caption" color="text.secondary" sx={{ alignSelf: "center" }}>
            The tool runs in a sandbox. Approve to install it.
          </Typography>
        </Box>
      ) : null}
    </Box>
  );
}
```

### 6. ChatInputBar

**`frontend/src/components/workspace/ChatInputBar.tsx`** (EDIT)

Multi-line auto-growing textarea with send button and file attach. Enter sends, Shift+Enter
adds newline. Disabled + spinner while `isStreaming`.

```tsx
// Props: onSend(text, fileIds), isStreaming, disabled
// State: text (string), files (File[] for display only - upload via API)
// Key handlers: Enter without shift -> onSend(text, []); clear text after send
// Send button: disabled when text.trim() is empty or isStreaming
// Stop button: appears instead of send when isStreaming, calls onStop()
// File attach: opens input[type="file"], uploads to POST /api/workspace/files
//   returns { id: string }, pushes id to fileIds array
// Layout: Box with border (1px solid divider), borderRadius 2, bgcolor background.paper
//   inner: Stack row with (IconButton attach, TextField multiline maxRows=8, IconButton send/stop)
```

For the textarea, use MUI `TextField` with `multiline`, `maxRows={8}`, `variant="standard"`,
`disableUnderline`. The border comes from the outer `Box`, not the TextField.

### 7. SessionList

**`frontend/src/components/chat/SessionList.tsx`** (EDIT)

Left sidebar list of all conversations, grouped by date (Today, Yesterday, Last 7 days, Older).

```tsx
// Data: useSWR("chat-sessions", () => fetchConversations(100))
// Each item: session title (truncated 40 chars), relative time
// Active item highlighted with primary.main left border
// "New conversation" button at top: navigates to /chat
// On item click: router.push(`/chat/${session.id}`)
// Empty state: "No conversations yet" with "Start one" button
// Skeleton: show 5 SkeletonText items while loading
```

Group sessions by `created_at` date using a helper function:
```ts
function groupByDate(sessions: Session[]): { label: string; items: Session[] }[] {
  const today = new Date();
  // groups: Today, Yesterday, Last 7 days, Older
  // return array in that order, omitting empty groups
}
```

### 8. ChatStatusBar

**`frontend/src/components/chat/ChatStatusBar.tsx`** (EDIT)

Thin bar above the input showing: active model name, streaming indicator (animated dot), stop button.

```tsx
// Props: modelId, models, isStreaming, onStop, onModelChange
// Layout: flex row, height 32, px 2, bgcolor rgba(0,0,0,0.15)
// Left: model name as a Select (small, variant="standard", no border)
// Right: if streaming -> animated "Responding..." + Stop button; else nothing
```

### 9. ThinkingBlock

**`frontend/src/components/chat/ThinkingBlock.tsx`** (EDIT)

Collapsible panel for extended thinking / chain-of-thought. Shown when the model returns
thinking blocks in the response.

```tsx
// Props: blocks: ContentBlock[] (where block.type === "thinking")
// Default: collapsed, showing "Thinking..." pill
// Expanded: shows the thinking text in a muted, smaller font box
// Same collapse pattern as ToolCallBlock
```

### 10. Verify useChat streaming hook wires correctly

**`frontend/src/hooks/useChat.ts`** (READ and verify - do not rewrite unless broken)

Confirm:
- `send(text, fileIds)` posts to `POST /api/workspace/conversations/{sessionId}/messages`
  with `{ content: text, file_ids: fileIds }` and then opens an SSE stream at
  `GET /api/workspace/conversations/{sessionId}/stream` (or the API uses a streaming POST).
- Incoming SSE events parse as `{ type: "delta" | "tool_call" | "mutation_staged" | "done", ... }`
  and update the `messages` state.
- `stop()` calls `DELETE /api/workspace/conversations/{sessionId}/stream` or closes the
  EventSource.
- `updateMutationStatus(toolCallId, status)` calls
  `POST /api/mutations/{toolCallId}/approve` or `/reject` and updates the local message state.

If the hook is fully implemented, no change needed. If it is a stub, implement it following
the patterns in `workspace-api.ts`.

### 11. CanvasPanel

**`frontend/src/components/chat/CanvasPanel.tsx`** (EDIT)

Slide-in side panel that shows code artifacts extracted from the conversation (the `canvas-blocks`
library already extracts these). Shows a tab per canvas block (filename + language).

```tsx
// Props: blocks: CanvasBlock[], open, onClose, width, onWidthChange
// Layout: Drawer anchored to right, resizable (drag handle on left edge)
// Each tab: filename chip. Active tab content: code block with line numbers
// "Copy" and "Download" actions per block
// If open is false, render nothing (save DOM budget)
```

### 12. Acceptance test (manual)

After implementing:

1. Open `http://localhost:3000/chat`. See the ChatEmptyState with wordmark and starter prompts.
2. Click a starter prompt. A new session is created and the user message appears in the feed.
3. The agent streams a response. Text appears token by token in the assistant bubble.
4. If the agent uses a tool, a collapsible ToolCallBlock appears with input/output.
5. Type a follow-up. Shift+Enter adds a newline. Enter sends.
6. The session appears in the left sidebar under "Today".
7. Click the session in the sidebar - it navigates to `/chat/{sessionId}` and the full history is visible.
8. Ask the agent something it cannot do (e.g. "Track my hours on this project"). The
   MutationApprovalBlock appears with a diff and Approve/Reject buttons.
9. Click "Approve". The block status chip changes to "approved" and the agent continues.
10. The stop button appears during streaming and cancels the response when clicked.
11. On mobile (375px viewport), the sidebar is hidden and accessible via hamburger.
