"use client";

import * as React from "react";
import type { SessionReplayData } from "@/types/brain-replay";

function transcriptText(data: SessionReplayData): string {
  const lines = [
    `# ${data.session_title}`,
    `Session: ${data.session_id}`,
    `Date: ${new Date(data.session_date).toLocaleString()}`,
    "",
  ];
  for (const message of data.messages) {
    const role = message.role === "user" ? "User" : "Aiva";
    lines.push(`${role}: ${message.content}`);
    const activations = [...message.activations_before, ...message.activations_during];
    if (activations.length > 0) {
      lines.push(`  Activated: ${activations.join(", ")}`);
    }
    lines.push("");
  }
  return lines.join("\n");
}

function activationCsv(data: SessionReplayData): string {
  const header = "step,timestamp,node_kind,node_id,label,relation,confidence";
  const rows = data.activations.map((activation) =>
    [
      activation.step,
      activation.activated_at,
      activation.node_kind,
      activation.node_id,
      JSON.stringify(activation.node_label),
      activation.relation,
      activation.confidence ?? "",
    ].join(","),
  );
  return [header, ...rows].join("\n");
}

function download(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function BrainReplayExport({ data }: { data: SessionReplayData }) {
  return {
    exportTranscript: () => download(`${data.session_id}-transcript.txt`, transcriptText(data), "text/plain"),
    exportActivationLog: () => download(`${data.session_id}-activations.csv`, activationCsv(data), "text/csv"),
  };
}

export function useBrainReplayExport(data: SessionReplayData | null) {
  return React.useMemo(() => {
    if (!data) {
      return {
        exportTranscript: () => undefined,
        exportActivationLog: () => undefined,
      };
    }
    return {
      exportTranscript: () => download(`${data.session_id}-transcript.txt`, transcriptText(data), "text/plain"),
      exportActivationLog: () => download(`${data.session_id}-activations.csv`, activationCsv(data), "text/csv"),
    };
  }, [data]);
}
