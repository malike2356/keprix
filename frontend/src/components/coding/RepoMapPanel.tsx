"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Typography from "@mui/material/Typography";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonChart } from "@/components/ui/loading";

type RepoMapPanelProps = {
  repoPath: string;
  compact?: string;
  files?: string[];
  tests?: string[];
  routes?: string[];
  recentlyChanged?: string[];
  ignoredCount?: number;
  loading?: boolean;
  error?: string | null;
};

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <Typography variant="overline" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
      {children}
    </Typography>
  );
}

export function RepoMapPanel({
  repoPath,
  compact = "",
  files = [],
  tests = [],
  routes = [],
  recentlyChanged = [],
  ignoredCount = 0,
  loading = false,
  error = null,
}: RepoMapPanelProps) {
  return (
    <DashboardCard
      title="Repo map"
      subtitle={repoPath || "No repository selected"}
      action={<Chip size="small" label={`${files.length} files`} variant="outlined" />}
    >
      {loading ? <SkeletonChart height={220} /> : null}
      {error ? (
        <Typography variant="body2" color="error">
          {error}
        </Typography>
      ) : null}

      {!loading && !error ? (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {recentlyChanged.length ? (
            <Box>
              <SectionLabel>Recently changed</SectionLabel>
              <Typography variant="body2">{recentlyChanged.slice(0, 8).join(", ")}</Typography>
            </Box>
          ) : null}

          <Box>
            <SectionLabel>Files</SectionLabel>
            {files.length ? (
              <List dense disablePadding sx={{ maxHeight: 220, overflow: "auto" }}>
                {files.slice(0, 40).map((file) => (
                  <ListItem key={file} disableGutters sx={{ py: 0.25 }}>
                    <Typography variant="caption" component="span" sx={{ fontFamily: "monospace" }}>
                      {file}
                    </Typography>
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No indexed files yet.
              </Typography>
            )}
          </Box>

          {tests.length ? (
            <Box>
              <SectionLabel>Tests</SectionLabel>
              <Typography variant="caption" sx={{ fontFamily: "monospace", display: "block" }}>
                {tests.slice(0, 10).join(", ")}
              </Typography>
            </Box>
          ) : null}

          {routes.length ? (
            <Box>
              <SectionLabel>Routes</SectionLabel>
              <Typography variant="caption" sx={{ fontFamily: "monospace", display: "block" }}>
                {routes.slice(0, 10).join(", ")}
              </Typography>
            </Box>
          ) : null}

          {compact ? (
            <Box>
              <SectionLabel>Compact map</SectionLabel>
              <Box
                component="pre"
                sx={{
                  m: 0,
                  p: 1.5,
                  maxHeight: 220,
                  overflow: "auto",
                  borderRadius: 1,
                  bgcolor: "action.hover",
                  fontSize: "0.75rem",
                }}
              >
                {compact}
              </Box>
            </Box>
          ) : null}

          <Typography variant="caption" color="text.secondary">
            Ignored paths and secrets excluded: {ignoredCount}
          </Typography>
        </Box>
      ) : null}
    </DashboardCard>
  );
}
