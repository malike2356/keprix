"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AgentAppDetail } from "@/lib/agent-apps-api";

type RunResult = {
  output?: string;
  status?: string;
  artifact?: unknown;
  artifact_path?: string;
  artifacts?: Array<{ path?: string; name?: string; url?: string }>;
  [key: string]: unknown;
};

type Props = {
  app?: AgentAppDetail;
  result: RunResult | null;
};

function primaryOutputType(app?: AgentAppDetail) {
  return app?.outputs?.[0]?.type ?? "text";
}

function extractArtifacts(result: RunResult | null) {
  if (!result) return [];
  const items: Array<{ label: string; href?: string }> = [];
  if (result.artifact_path) {
    items.push({ label: result.artifact_path, href: result.artifact_path });
  }
  if (Array.isArray(result.artifacts)) {
    for (const item of result.artifacts) {
      if (!item || typeof item !== "object") continue;
      const label = String(item.name || item.path || "artifact");
      items.push({ label, href: item.url || item.path });
    }
  }
  if (result.artifact && typeof result.artifact === "object") {
    const artifact = result.artifact as Record<string, unknown>;
    items.push({
      label: String(artifact.name || artifact.type || "artifact"),
      href: typeof artifact.path === "string" ? artifact.path : undefined,
    });
  }
  return items;
}

export default function AgentAppOutput({ app, result }: Props) {
  if (!result) return null;

  const outputType = primaryOutputType(app);
  const artifacts = extractArtifacts(result);
  const outputText =
    typeof result.output === "string"
      ? result.output
      : outputType === "json"
        ? JSON.stringify(result, null, 2)
        : JSON.stringify(result, null, 2);

  return (
    <Box sx={{ bgcolor: "action.hover", borderRadius: 1, p: 2 }}>
      <Typography variant="subtitle2" gutterBottom>
        Output
      </Typography>

      {outputType === "markdown" ? (
        <Box className="markdown-body" sx={{ "& p": { mt: 0, mb: 1 } }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{outputText}</ReactMarkdown>
        </Box>
      ) : outputType === "json" ? (
        <Typography component="pre" variant="body2" sx={{ whiteSpace: "pre-wrap", m: 0 }}>
          {outputText}
        </Typography>
      ) : (
        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
          {outputText}
        </Typography>
      )}

      {outputType === "file" || artifacts.length ? (
        <Box sx={{ mt: 2, display: "grid", gap: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Artifacts
          </Typography>
          {artifacts.length ? (
            artifacts.map((item) =>
              item.href ? (
                <Button key={item.label} size="small" href={item.href} target="_blank" rel="noreferrer">
                  Download {item.label}
                </Button>
              ) : (
                <Typography key={item.label} variant="body2">
                  {item.label}
                </Typography>
              ),
            )
          ) : (
            <Typography variant="body2" color="text.secondary">
              No downloadable artifacts in this run.
            </Typography>
          )}
        </Box>
      ) : null}
    </Box>
  );
}
