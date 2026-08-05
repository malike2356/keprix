"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import AddIcon from "@mui/icons-material/Add";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import StartPlaybookDialog, { usePlaybookTemplates } from "@/components/playbooks/StartPlaybookDialog";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonBlock, SkeletonTable } from "@/components/ui/loading";
import {
  fetchPlaybookRuns,
  type PlaybookGraphTemplate,
  type PlaybookRunStatus,
} from "@/lib/playbook-api";

function statusColor(
  status: PlaybookRunStatus,
): "default" | "success" | "warning" | "error" | "info" {
  if (status === "completed") return "success";
  if (status === "failed" || status === "cancelled") return "error";
  if (status === "running" || status === "pending") return "info";
  if (status === "interrupted" || status === "waiting_for_approval") return "warning";
  return "default";
}

function shortRunId(runId: string): string {
  return runId.length > 12 ? `${runId.slice(0, 8)}...` : runId;
}

function TemplateCard({
  template,
  onStart,
}: {
  template: PlaybookGraphTemplate;
  onStart: (graphId: string) => void;
}) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="h6">{template.title}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 2 }}>
          {template.description}
        </Typography>
        <Chip size="small" label={template.graph_id} sx={{ mr: 1 }} />
        <Button size="small" startIcon={<PlayArrowIcon />} onClick={() => onStart(template.graph_id)}>
          Start
        </Button>
      </CardContent>
    </Card>
  );
}

export default function PlaybooksPage() {
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [selectedGraph, setSelectedGraph] = React.useState<string | undefined>();
  const { templates, loading: templatesLoading } = usePlaybookTemplates();
  const { data, error, isLoading, mutate } = useSWR("playbook-runs", () => fetchPlaybookRuns());

  const runs = data?.runs ?? [];

  const openStart = (graphId?: string) => {
    setSelectedGraph(graphId);
    setDialogOpen(true);
  };

  return (
    <Box>
      <PageHeader
        title="Playbooks"
        description="Durable workflow graphs with checkpoints, interrupts, and resume."
        actions={
          <>
            <Button component={Link} href="/playbooks/triggers" variant="outlined">
              Triggers
            </Button>
            <Button component={Link} href="/playbooks/studio/new" variant="outlined" startIcon={<AddIcon />}>
              New in Studio
            </Button>
            <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={() => openStart()}>
              Start run
            </Button>
          </>
        }
      />

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error instanceof Error ? error.message : "Failed to load playbook runs"}
        </Alert>
      ) : null}

      <Typography variant="h6" sx={{ mb: 1 }}>
        Templates
      </Typography>
      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" },
          mb: 4,
        }}
      >
        {templatesLoading ? (
          <>
            <SkeletonBlock height={140} />
            <SkeletonBlock height={140} />
            <SkeletonBlock height={140} />
          </>
        ) : (
          templates.map((template) => (
            <TemplateCard key={template.graph_id} template={template} onStart={openStart} />
          ))
        )}
      </Box>

      <Typography variant="h6" sx={{ mb: 1 }}>
        Recent runs
      </Typography>
      {isLoading ? (
        <SkeletonTable rows={5} columns={4} />
      ) : runs.length === 0 ? (
        <EmptyState
          title="No playbook runs yet"
          description="Start a template run or open the borehole Ghana example playbook YAML."
          actionLabel="Start run"
          onAction={() => openStart("sdk-workflow")}
        />
      ) : (
        <Card variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Run</TableCell>
                <TableCell>Playbook</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Open</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {runs.map((run) => (
                <TableRow key={run.run_id} hover>
                  <TableCell>
                    <Typography variant="body2" fontFamily="monospace">
                      {shortRunId(run.run_id)}
                    </Typography>
                  </TableCell>
                  <TableCell>{run.graph_id}</TableCell>
                  <TableCell>
                    <Chip size="small" color={statusColor(run.status)} label={run.status} />
                  </TableCell>
                  <TableCell align="right">
                    <Button component={Link} href={`/playbooks/${run.run_id}`} size="small">
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
        Example domain playbook:{" "}
        <Link href="/docs">examples/borehole-ghana/playbook.yaml</Link> (see repository docs).
      </Typography>

      <StartPlaybookDialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
          void mutate();
        }}
        templates={templates}
        defaultGraphId={selectedGraph}
      />
    </Box>
  );
}
