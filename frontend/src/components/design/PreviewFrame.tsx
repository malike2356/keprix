"use client";

import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import * as React from "react";
import { getApiBaseUrl } from "@/lib/ce-api";

type PreviewFrameProps = {
  sessionId: string | null;
  previewUrl: string | null;
  onSelection: (payload: Record<string, unknown>) => void;
};

export default function PreviewFrame({ sessionId, previewUrl, onSelection }: PreviewFrameProps) {
  const [reloadKey, setReloadKey] = React.useState(0);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    const listener = (event: MessageEvent) => {
      const payload = event.data as { type?: string; session_id?: string };
      if (payload?.type !== "keprix-design-selection") {
        return;
      }
      if (sessionId && payload.session_id !== sessionId) {
        return;
      }
      onSelection(event.data as Record<string, unknown>);
    };
    window.addEventListener("message", listener);
    return () => window.removeEventListener("message", listener);
  }, [onSelection, sessionId]);

  React.useEffect(() => {
    if (!sessionId) {
      return undefined;
    }
    const eventSource = new EventSource(`${getApiBaseUrl()}/api/design/preview/${encodeURIComponent(sessionId)}/events`);
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as { type?: string };
        if (data.type === "reload") {
          setReloadKey((current) => current + 1);
        }
      } catch {
        // Ignore malformed event-stream rows.
      }
    };
    return () => eventSource.close();
  }, [sessionId]);

  if (!previewUrl) {
    return (
      <Box sx={{ minHeight: 420, border: "1px dashed", borderColor: "divider", display: "grid", placeItems: "center" }} />
    );
  }

  return (
    <Box sx={{ border: "1px solid", borderColor: "divider", minHeight: 560, position: "relative", bgcolor: "background.paper" }}>
      {loading ? <LinearProgress sx={{ position: "absolute", top: 0, left: 0, right: 0, zIndex: 1 }} /> : null}
      <iframe
        key={`${previewUrl}-${reloadKey}`}
        src={`${getApiBaseUrl()}${previewUrl}`}
        title="Design preview"
        sandbox="allow-scripts allow-same-origin allow-forms"
        onLoad={() => setLoading(false)}
        referrerPolicy="no-referrer"
        style={{ width: "100%", height: 560, border: 0, display: "block" }}
      />
    </Box>
  );
}
