"use client";

import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import * as React from "react";

type DiffFile = {
  path: string;
  hunks: DiffHunk[];
};

type DiffHunk = {
  header: string;
  lines: DiffLine[];
};

type DiffLine = {
  type: "add" | "remove" | "context";
  content: string;
};

function parseUnifiedDiff(diff: string): DiffFile[] {
  const files: DiffFile[] = [];
  let current: DiffFile | null = null;
  let currentHunk: DiffHunk | null = null;

  for (const rawLine of diff.split("\n")) {
    if (rawLine.startsWith("+++ ") || rawLine.startsWith("--- ")) {
      if (rawLine.startsWith("+++ ")) {
        const path = rawLine.slice(4).replace(/^b\//, "").trim();
        current = { path, hunks: [] };
        files.push(current);
      }
      continue;
    }
    if (rawLine.startsWith("@@")) {
      currentHunk = { header: rawLine, lines: [] };
      current?.hunks.push(currentHunk);
      continue;
    }
    if (!currentHunk) continue;
    if (rawLine.startsWith("+")) {
      currentHunk.lines.push({ type: "add", content: rawLine.slice(1) });
    } else if (rawLine.startsWith("-")) {
      currentHunk.lines.push({ type: "remove", content: rawLine.slice(1) });
    } else {
      currentHunk.lines.push({ type: "context", content: rawLine.startsWith(" ") ? rawLine.slice(1) : rawLine });
    }
  }

  if (files.length === 0 && diff.trim()) {
    return [{ path: "changes", hunks: [{ header: "", lines: diff.split("\n").map((line) => ({ type: "context" as const, content: line })) }] }];
  }
  return files;
}

function lineSx(type: DiffLine["type"]) {
  if (type === "add") {
    return {
      bgcolor: (theme: { palette: { mode: string; success: { main: string } } }) =>
        alpha(theme.palette.success.main, theme.palette.mode === "dark" ? 0.18 : 0.12),
      color: "text.primary",
    };
  }
  if (type === "remove") {
    return {
      bgcolor: (theme: { palette: { mode: string; error: { main: string } } }) =>
        alpha(theme.palette.error.main, theme.palette.mode === "dark" ? 0.18 : 0.12),
      color: "text.primary",
    };
  }
  return { bgcolor: "transparent", color: "text.secondary" };
}

type DiffViewerProps = {
  diff: string;
  defaultExpanded?: boolean;
};

export default function DiffViewer({ diff, defaultExpanded = true }: DiffViewerProps) {
  const files = React.useMemo(() => parseUnifiedDiff(diff), [diff]);
  const [selected, setSelected] = React.useState(files[0]?.path ?? "");

  React.useEffect(() => {
    if (!selected && files[0]) {
      setSelected(files[0].path);
    }
  }, [files, selected]);

  const active = files.find((file) => file.path === selected) ?? files[0];

  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "220px 1fr" }, gap: 2 }}>
      <Box sx={{ display: "grid", gap: 0.5, alignContent: "start" }}>
        <Typography variant="overline" color="text.secondary">
          Files
        </Typography>
        {files.map((file) => (
          <Box
            key={file.path}
            onClick={() => setSelected(file.path)}
            sx={{
              px: 1,
              py: 0.75,
              borderRadius: 1,
              cursor: "pointer",
              bgcolor: selected === file.path ? "action.selected" : "transparent",
              fontFamily: "monospace",
              fontSize: 12,
            }}
          >
            {file.path}
          </Box>
        ))}
      </Box>
      <Box sx={{ display: "grid", gap: 1 }}>
        {active ? (
          <Accordion defaultExpanded={defaultExpanded} disableGutters elevation={0} sx={{ border: 1, borderColor: "divider" }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                {active.path}
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ p: 0 }}>
              <Box
                component="pre"
                sx={{
                  m: 0,
                  p: 1.5,
                  overflow: "auto",
                  fontFamily: "monospace",
                  fontSize: 12,
                  lineHeight: 1.5,
                  maxHeight: 480,
                }}
              >
                {active.hunks.map((hunk, index) => (
                  <Box key={`${active.path}-${index}`} sx={{ mb: 1 }}>
                    {hunk.header ? (
                      <Typography component="div" variant="caption" color="primary" sx={{ fontFamily: "monospace" }}>
                        {hunk.header}
                      </Typography>
                    ) : null}
                    {hunk.lines.map((line, lineIndex) => (
                      <Box
                        key={`${index}-${lineIndex}`}
                        component="div"
                        sx={{
                          ...lineSx(line.type),
                          whiteSpace: "pre-wrap",
                          px: 0.5,
                        }}
                      >
                        {line.type === "add" ? "+" : line.type === "remove" ? "-" : " "}
                        {line.content}
                      </Box>
                    ))}
                  </Box>
                ))}
              </Box>
            </AccordionDetails>
          </Accordion>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No diff content.
          </Typography>
        )}
      </Box>
    </Box>
  );
}
