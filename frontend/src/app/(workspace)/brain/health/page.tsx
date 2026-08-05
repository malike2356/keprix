"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Grid from "@mui/material/Grid2";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import BrainSectionTabs from "@/components/memory/BrainSectionTabs";
import BrainHealthScore from "@/components/brain/BrainHealthScore";
import CoverageGapList from "@/components/brain/CoverageGapList";
import DuplicateMerger from "@/components/brain/DuplicateMerger";
import HubNodeList from "@/components/brain/HubNodeList";
import OrphanNodeList from "@/components/brain/OrphanNodeList";
import { useBrainHealth } from "@/hooks/useBrainHealth";
import { archiveStaleNodes, deleteOrphanNodes, mergeDuplicateNodes } from "@/lib/brain-health-api";

const KIND_CARDS = ["memory", "skill", "task", "document"] as const;

export default function BrainHealthPage() {
  const { report, loading, error, refresh } = useBrainHealth();
  const [message, setMessage] = React.useState<string | null>(null);
  const [archiveOpen, setArchiveOpen] = React.useState(false);
  const [archiveBusy, setArchiveBusy] = React.useState(false);

  const handleDeleteOrphans = async () => {
    const deleted = await deleteOrphanNodes();
    setMessage(`Deleted ${deleted} orphan node(s).`);
    await refresh();
  };

  const handleMerge = async (keepId: string, deleteId: string) => {
    await mergeDuplicateNodes(keepId, deleteId);
    setMessage("Duplicate memories merged.");
    await refresh();
  };

  const handleArchiveStale = async () => {
    if (!report?.stale_nodes.length) return;
    setArchiveBusy(true);
    try {
      const archived = await archiveStaleNodes(report.stale_nodes.map((node) => node.id));
      setMessage(`Archived ${archived} stale node(s).`);
      setArchiveOpen(false);
      await refresh();
    } finally {
      setArchiveBusy(false);
    }
  };

  return (
    <Box sx={{ display: "grid", gap: 2, pb: 4 }}>
      <PageHeader
        title="Brain"
        description="Coverage and cleanup for your workspace knowledge graph."
      />
      <BrainSectionTabs value="health" />

      {error ? <Typography color="error">{error}</Typography> : null}
      {message ? <Typography color="text.secondary">{message}</Typography> : null}

      <BrainHealthScore
        score={report?.health_score ?? 0}
        label={report?.health_label ?? "..."}
        generatedAt={report?.generated_at}
        loading={loading}
        onRefresh={() => {
          void refresh();
        }}
      />

      <Grid container spacing={1.5}>
        {KIND_CARDS.map((kind) => (
          <Grid key={kind} size={{ xs: 6, md: 3 }}>
            <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1.5, p: 1.5, textAlign: "center" }}>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: "capitalize" }}>
                {kind === "memory" ? "Memories" : `${kind}s`}
              </Typography>
              <Typography variant="h5">{report?.nodes_by_kind[kind] ?? 0}</Typography>
            </Box>
          </Grid>
        ))}
      </Grid>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip color="warning" label={`${report?.orphan_count ?? 0} orphan nodes`} />
        <Chip color="default" label={`${report?.stale_count ?? 0} stale memories`} />
        <Chip color="warning" variant="outlined" label={`${report?.duplicate_pairs?.length ?? 0} duplicate pairs`} />
        {report?.stale_count ? (
          <Chip
            clickable
            label="Archive stale"
            onClick={() => setArchiveOpen(true)}
            variant="outlined"
          />
        ) : null}
      </Stack>

      <Dialog open={archiveOpen} onClose={() => !archiveBusy && setArchiveOpen(false)}>
        <DialogTitle>Archive stale nodes?</DialogTitle>
        <DialogContent>
          <Typography>
            Archive {report?.stale_count ?? 0} stale node(s)? They will be hidden from the normal graph view but remain recoverable.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setArchiveOpen(false)} disabled={archiveBusy}>Cancel</Button>
          <Button variant="contained" onClick={() => void handleArchiveStale()} disabled={archiveBusy}>
            Archive {report?.stale_count ?? 0}
          </Button>
        </DialogActions>
      </Dialog>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <OrphanNodeList nodes={report?.orphan_nodes ?? []} onDeleteAll={handleDeleteOrphans} />
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <DuplicateMerger pairs={report?.duplicate_pairs ?? []} onMerge={handleMerge} />
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <HubNodeList nodes={report?.hub_nodes ?? []} />
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <CoverageGapList gaps={report?.coverage_gaps ?? []} />
        </Grid>
      </Grid>
    </Box>
  );
}
