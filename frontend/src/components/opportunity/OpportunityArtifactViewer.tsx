"use client";

import Box from "@mui/material/Box";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import { fetchOpportunityArtifact } from "@/lib/opportunity-api";

const ARTIFACT_OPTIONS = [
  "01-market-demand.md",
  "02-pain-mining.md",
  "03-icp.md",
  "04-competitors.md",
  "05-offer-doc.md",
  "06-pricing.md",
  "07-funnel.md",
  "08-content-assets.md",
  "09-ads.md",
  "10-sales-deck.md",
  "11-launch-plan.md",
  "12-validation-score.md",
  "14-growth-loop.md",
  "agent-memory-brief.md",
];

type Props = {
  opportunityId: string;
  initialFilename?: string;
};

export default function OpportunityArtifactViewer({ opportunityId, initialFilename }: Props) {
  const [filename, setFilename] = React.useState(initialFilename ?? "05-offer-doc.md");
  const [content, setContent] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const row = await fetchOpportunityArtifact(opportunityId, filename);
        if (!cancelled) {
          setContent(row.content);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Load failed");
          setContent("");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [opportunityId, filename]);

  return (
    <Box>
      <Select
        size="small"
        value={filename}
        onChange={(e) => setFilename(String(e.target.value))}
        sx={{ mb: 1, minWidth: 240 }}
      >
        {ARTIFACT_OPTIONS.map((name) => (
          <MenuItem key={name} value={name}>
            {name}
          </MenuItem>
        ))}
      </Select>
      {error ? (
        <Typography variant="body2" color="error">
          {error}
        </Typography>
      ) : loading ? (
        <SkeletonDetailPanel fields={5} />
      ) : (
        <Box
          component="pre"
          sx={{
            m: 0,
            p: 2,
            border: 1,
            borderColor: "divider",
            borderRadius: 1,
            fontSize: 12,
            whiteSpace: "pre-wrap",
            maxHeight: 480,
            overflow: "auto",
          }}
        >
          {content}
        </Box>
      )}
    </Box>
  );
}
