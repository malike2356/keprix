"use client";

import CloseIcon from "@mui/icons-material/Close";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DownloadIcon from "@mui/icons-material/Download";
import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export type CanvasBlock =
  | { type: "markdown"; content: string }
  | { type: "code"; language: string; content: string }
  | { type: "image"; url: string; alt?: string }
  | { type: "mermaid"; content: string };

type CanvasPanelProps = {
  open: boolean;
  blocks: CanvasBlock[];
  onClose: () => void;
  width?: number;
  onWidthChange?: (width: number) => void;
};

export default function CanvasPanel({
  open,
  blocks,
  onClose,
  width = 360,
  onWidthChange,
}: CanvasPanelProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const [resizing, setResizing] = React.useState(false);
  const [activeIndex, setActiveIndex] = React.useState(0);
  const startX = React.useRef(0);
  const startWidth = React.useRef(width);

  React.useEffect(() => {
    if (activeIndex >= blocks.length) {
      setActiveIndex(0);
    }
  }, [activeIndex, blocks.length]);

  const copyBlock = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
    } catch {
      // ignore clipboard failures
    }
  };

  const downloadBlock = (content: string, filename: string) => {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const blockLabel = (block: CanvasBlock, index: number) => {
    if (block.type === "code") return `${block.language || "code"}-${index + 1}`;
    if (block.type === "mermaid") return `diagram-${index + 1}`;
    if (block.type === "image") return block.alt || `image-${index + 1}`;
    return `markdown-${index + 1}`;
  };

  const blockContent = (block: CanvasBlock) => {
    if (block.type === "markdown" || block.type === "code" || block.type === "mermaid") {
      return block.content;
    }
    return block.url;
  };

  React.useEffect(() => {
    if (!resizing) {
      return;
    }
    const onMove = (event: MouseEvent) => {
      const next = Math.min(640, Math.max(280, startWidth.current - (event.clientX - startX.current)));
      onWidthChange?.(next);
    };
    const onUp = () => setResizing(false);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [resizing, onWidthChange]);

  const body = (
    <Paper
      elevation={isMobile ? 8 : 0}
      sx={{
        width: isMobile ? "100vw" : width,
        minWidth: isMobile ? "100vw" : width,
        height: "100%",
        borderLeft: isMobile ? 0 : 1,
        borderColor: "divider",
        display: "flex",
        flexDirection: "column",
        position: isMobile ? "fixed" : "relative",
        inset: isMobile ? 0 : undefined,
        zIndex: isMobile ? theme.zIndex.modal : undefined,
      }}
    >
      {!isMobile ? (
        <Box
          onMouseDown={(e) => {
            setResizing(true);
            startX.current = e.clientX;
            startWidth.current = width;
          }}
          sx={{
            position: "absolute",
            left: 0,
            top: 0,
            bottom: 0,
            width: 6,
            cursor: "col-resize",
            zIndex: 2,
          }}
        />
      ) : null}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            px: 2,
            py: 1,
            borderBottom: 1,
            borderColor: "divider",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <OpenInFullIcon fontSize="small" color="action" />
            <Typography variant="subtitle2">Canvas</Typography>
          </Box>
          <IconButton size="small" onClick={onClose}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>
        <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
          {blocks.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              Structured agent output will appear here.
            </Typography>
          ) : (
            <>
              {blocks.length > 1 ? (
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 2 }}>
                  {blocks.map((block, index) => (
                    <Chip
                      key={`${block.type}-${index}`}
                      size="small"
                      label={blockLabel(block, index)}
                      color={index === activeIndex ? "primary" : "default"}
                      onClick={() => setActiveIndex(index)}
                      variant={index === activeIndex ? "filled" : "outlined"}
                    />
                  ))}
                </Box>
              ) : null}
              {blocks.map((block, index) => (
                <Box key={`${block.type}-${index}`} sx={{ display: index === activeIndex ? "block" : "none", mb: 2 }}>
                  <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1, mb: 1 }}>
                    <Button
                      size="small"
                      startIcon={<ContentCopyIcon />}
                      onClick={() => void copyBlock(blockContent(block))}
                    >
                      Copy
                    </Button>
                    <Button
                      size="small"
                      startIcon={<DownloadIcon />}
                      onClick={() => downloadBlock(blockContent(block), `${blockLabel(block, index)}.txt`)}
                    >
                      Download
                    </Button>
                  </Box>
                  {block.type === "markdown" && (
                  <Box sx={{ "& table": { width: "100%", borderCollapse: "collapse" }, "& th, & td": { border: 1, borderColor: "divider", p: 1 } }}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{block.content}</ReactMarkdown>
                  </Box>
                )}
                {block.type === "code" && (
                  <Box
                    component="pre"
                    sx={{
                      m: 0,
                      p: 1.5,
                      bgcolor: "action.hover",
                      borderRadius: 1,
                      overflow: "auto",
                      fontSize: "0.8rem",
                    }}
                  >
                    <Typography component="span" variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                      {block.language}
                    </Typography>
                    {block.content}
                  </Box>
                )}
                {block.type === "image" && (
                  <Box component="img" src={block.url} alt={block.alt || "output"} sx={{ maxWidth: "100%", borderRadius: 1 }} />
                )}
                {block.type === "mermaid" && (
                  <Box
                    component="pre"
                    sx={{ m: 0, p: 1.5, bgcolor: "action.hover", borderRadius: 1, fontSize: "0.75rem" }}
                  >
                    {block.content}
                  </Box>
                )}
              </Box>
              ))}
            </>
          )}
        </Box>
      </Paper>
  );

  if (isMobile) {
    return open ? body : null;
  }

  return (
    <Collapse in={open} orientation="horizontal">
      {body}
    </Collapse>
  );
}

export function parseCanvasBlocksFromText(text: string): CanvasBlock[] {
  const blocks: CanvasBlock[] = [];
  const codeRegex = /```(\w+)?\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = codeRegex.exec(text)) !== null) {
    const before = text.slice(lastIndex, match.index).trim();
    if (before) {
      blocks.push({ type: "markdown", content: before });
    }
    const lang = match[1] || "text";
    const content = match[2];
    if (lang === "mermaid") {
      blocks.push({ type: "mermaid", content });
    } else {
      blocks.push({ type: "code", language: lang, content });
    }
    lastIndex = match.index + match[0].length;
  }
  const tail = text.slice(lastIndex).trim();
  if (tail) {
    blocks.push({ type: "markdown", content: tail });
  }
  return blocks;
}
