import type { CanvasBlock } from "@/components/chat/CanvasPanel";
import type { WorkspaceMessage } from "@/lib/workspace-api";

function isMarkdownTable(text: string): boolean {
  const lines = text.split("\n").filter((line) => line.trim());
  return lines.length >= 2 && lines.some((line) => line.includes("|"));
}

export function extractCanvasBlocks(messages: WorkspaceMessage[]): CanvasBlock[] {
  const blocks: CanvasBlock[] = [];

  for (const message of messages) {
    if (message.role !== "assistant") {
      continue;
    }
    for (const block of message.content) {
      if (block.type === "code") {
        if (block.language.toLowerCase() === "mermaid") {
          blocks.push({ type: "mermaid", content: block.content });
        } else {
          blocks.push({ type: "code", language: block.language, content: block.content });
        }
        continue;
      }
      if (block.type === "text") {
        const text = block.content.trim();
        if (!text) {
          continue;
        }
        if (text.includes("```mermaid") || isMarkdownTable(text) || text.includes("```")) {
          blocks.push({ type: "markdown", content: text });
        }
      }
    }
  }

  return blocks;
}
