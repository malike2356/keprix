"use client";

import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Box from "@mui/material/Box";

export type DataSectionTab =
  | "datasets"
  | "jobs"
  | "ml"
  | "export"
  | "rag"
  | "models"
  | "video"
  | "analytics"
  | "usage"
  | "observability";

export type DataSectionMeta = {
  value: DataSectionTab;
  label: string;
  title: string;
  description: string;
};

export const DATA_SECTIONS: DataSectionMeta[] = [
  {
    value: "datasets",
    label: "Datasets",
    title: "Data plane datasets",
    description: "Import tabular datasets, browse catalog versions, and run constrained SQL.",
  },
  {
    value: "jobs",
    label: "Jobs",
    title: "Background jobs",
    description: "Local job queue status, cancel, and dead-letter retry.",
  },
  {
    value: "ml",
    label: "ML",
    title: "ML workspace",
    description: "Experiments, runs, metrics, and model registry entries.",
  },
  {
    value: "export",
    label: "Export",
    title: "Document export",
    description: "Cover page, classification, and signatory exports via /api/export.",
  },
  {
    value: "rag",
    label: "RAG",
    title: "RAG Pipelines",
    description: "Ingest sources, run retrieval pipelines, and review grounded answers.",
  },
  {
    value: "models",
    label: "Local models",
    title: "Local models",
    description: "Hardware fit + Ollama/local serve for offline inference.",
  },
  {
    value: "video",
    label: "Video",
    title: "Video ingest",
    description: "Create transcript and frame manifests from URLs, paths, or uploaded files.",
  },
  {
    value: "analytics",
    label: "Data analysis",
    title: "Analyze your data",
    description: "Upload a file or paste data, ask a question, and get an instant answer with a chart.",
  },
  {
    value: "usage",
    label: "Usage",
    title: "LLM usage",
    description: "Token consumption and estimated spend. Reliability traces live under Observability.",
  },
  {
    value: "observability",
    label: "Observability",
    title: "Observability",
    description: "Runtime health: latency, errors, and agent traces. Spend lives under LLM usage.",
  },
];

export function parseDataTab(raw: string | null | undefined): DataSectionTab {
  const value = (raw || "").trim().toLowerCase();
  if (DATA_SECTIONS.some((section) => section.value === value)) {
    return value as DataSectionTab;
  }
  return "datasets";
}

export function dataHref(tab: DataSectionTab, extra?: URLSearchParams | Record<string, string | null | undefined>): string {
  const params = extra instanceof URLSearchParams ? new URLSearchParams(extra) : new URLSearchParams();
  if (extra && !(extra instanceof URLSearchParams)) {
    Object.entries(extra).forEach(([key, value]) => {
      if (value == null || value === "") params.delete(key);
      else params.set(key, value);
    });
  }
  params.set("tab", tab);
  const query = params.toString();
  return query ? `/data?${query}` : `/data?tab=${tab}`;
}

type DataSectionTabsProps = {
  value: DataSectionTab;
  onChange: (next: DataSectionTab) => void;
};

export default function DataSectionTabs({ value, onChange }: DataSectionTabsProps) {
  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
      <Tabs
        value={value}
        onChange={(_event, next: DataSectionTab) => onChange(next)}
        variant="scrollable"
        allowScrollButtonsMobile
        aria-label="Data workspace sections"
        sx={{
          minHeight: 36,
          "& .MuiTab-root": {
            minHeight: 36,
            textTransform: "none",
            fontWeight: 500,
            color: "text.secondary",
            px: 1.25,
            py: 0,
          },
          "& .Mui-selected": {
            color: "text.primary",
            fontWeight: 600,
          },
          "& .MuiTabs-indicator": {
            height: 2,
            borderRadius: 1,
          },
        }}
      >
        {DATA_SECTIONS.map((tab) => (
          <Tab key={tab.value} label={tab.label} value={tab.value} />
        ))}
      </Tabs>
    </Box>
  );
}
