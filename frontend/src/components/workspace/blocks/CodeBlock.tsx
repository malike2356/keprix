"use client";

import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { alpha, useTheme } from "@mui/material/styles";
import hljs from "highlight.js/lib/core";
import python from "highlight.js/lib/languages/python";
import typescript from "highlight.js/lib/languages/typescript";
import yaml from "highlight.js/lib/languages/yaml";
import * as React from "react";

hljs.registerLanguage("python", python);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("yaml", yaml);

type CodeBlockProps = {
  language: string;
  content: string;
};

function useHighlightTheme(mode: "light" | "dark") {
  React.useEffect(() => {
    const id = "keprix-hljs-theme";
    let link = document.getElementById(id) as HTMLLinkElement | null;
    if (!link) {
      link = document.createElement("link");
      link.id = id;
      link.rel = "stylesheet";
      document.head.appendChild(link);
    }
    link.href =
      mode === "dark"
        ? "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/github-dark.min.css"
        : "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/github.min.css";
  }, [mode]);
}

export default function CodeBlock({ language, content }: CodeBlockProps) {
  const theme = useTheme();
  const [copied, setCopied] = React.useState(false);
  useHighlightTheme(theme.palette.mode);

  const highlighted = React.useMemo(() => {
    try {
      if (hljs.getLanguage(language)) {
        return hljs.highlight(content, { language }).value;
      }
      return hljs.highlightAuto(content).value;
    } catch {
      return content;
    }
  }, [content, language]);

  const onCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <Box
      sx={{
        border: 1,
        borderColor: "divider",
        borderRadius: 2,
        overflow: "hidden",
        bgcolor: "background.paper",
        color: "text.primary",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 1.5,
          py: 0.75,
          borderBottom: 1,
          borderColor: "divider",
          bgcolor: "action.hover",
        }}
      >
        <Typography variant="caption" color="text.secondary">
          {language}
        </Typography>
        <Tooltip title={copied ? "Copied" : "Copy"}>
          <IconButton size="small" onClick={onCopy} aria-label="Copy code" color="inherit">
            <ContentCopyIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
      <Box
        component="pre"
        sx={{
          m: 0,
          p: 1.5,
          maxHeight: 400,
          overflow: "auto",
          fontSize: 13,
          lineHeight: 1.5,
          bgcolor: (t) =>
            t.palette.mode === "dark"
              ? alpha(t.palette.common.black, 0.35)
              : alpha(t.palette.common.black, 0.03),
          color: "text.primary",
          "& .hljs": { background: "transparent", color: "inherit" },
        }}
      >
        <Box component="code" sx={{ fontFamily: "monospace" }} dangerouslySetInnerHTML={{ __html: highlighted }} />
      </Box>
    </Box>
  );
}
