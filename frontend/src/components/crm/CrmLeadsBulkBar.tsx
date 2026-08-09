"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import {
  approveCrmApproval,
  bulkArchiveCrmLeads,
  bulkPatchCrmLeads,
  createCrmWorkflow,
  exportCrmLeadsWorkbook,
} from "@/lib/crm-api";
import { CRM_WORKSPACE, type CrmRecord } from "@/components/crm/types";

type CrmLeadsBulkBarProps = {
  selected: CrmRecord[];
  workspaceId?: string;
  filter?: Record<string, unknown>;
  onDone: () => void;
};

const PAYING = new Set(["customer", "paying"]);

export default function CrmLeadsBulkBar({
  selected,
  workspaceId = CRM_WORKSPACE,
  filter,
  onDone,
}: CrmLeadsBulkBarProps) {
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [tag, setTag] = React.useState("");
  const [owner, setOwner] = React.useState("");
  const [stage, setStage] = React.useState("");
  const [priority, setPriority] = React.useState("");
  const [listId, setListId] = React.useState("");
  const [campaignId, setCampaignId] = React.useState("");
  const [softWall, setSoftWall] = React.useState<{
    approvalId: string;
    pendingPatch: Record<string, unknown>;
    kind: string;
  } | null>(null);

  if (selected.length === 0) return null;

  const ids = selected.map((r) => r.id);
  const versions = Object.fromEntries(
    selected.filter((r) => typeof r.version === "number").map((r) => [r.id, r.version as number]),
  );

  const runPatch = async (patch: Record<string, unknown>, extra?: { tags_add?: string[]; add_to_list_id?: string; approval_id?: string }) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await bulkPatchCrmLeads(
        {
          ids,
          patch,
          expected_versions: versions,
          tags_add: extra?.tags_add,
          add_to_list_id: extra?.add_to_list_id,
          approval_id: extra?.approval_id,
        },
        workspaceId,
      );
      if (result.blocked && result.approval?.id) {
        setSoftWall({
          approvalId: String(result.approval.id),
          pendingPatch: patch,
          kind: String(result.error_code || "soft_wall_required"),
        });
        setMessage("Soft Wall approval required for this bulk change.");
        return;
      }
      setMessage(`Updated ${result.updated.length} lead(s); failed ${result.failed.length}.`);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk patch failed");
    } finally {
      setBusy(false);
    }
  };

  const approveAndRetry = async () => {
    if (!softWall) return;
    setBusy(true);
    try {
      await approveCrmApproval(softWall.approvalId, workspaceId);
      await runPatch(softWall.pendingPatch, { approval_id: softWall.approvalId });
      setSoftWall(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Soft Wall approve failed");
    } finally {
      setBusy(false);
    }
  };

  const onStage = async () => {
    if (!stage.trim()) return;
    if (PAYING.has(stage.trim())) {
      setSoftWall({ approvalId: "", pendingPatch: { stage: stage.trim(), pipeline_stage: stage.trim() }, kind: "preview" });
    }
    await runPatch({ stage: stage.trim(), pipeline_stage: stage.trim() });
  };

  const onExport = async (format: "xlsx" | "csv") => {
    setBusy(true);
    setError(null);
    try {
      const blob = await exportCrmLeadsWorkbook(
        ids.length ? { ids, format } : { filter: filter || {}, format },
        workspaceId,
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `keprix-leads.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      setMessage(`Exported ${format.toUpperCase()} for ${ids.length || "filtered"} lead(s).`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusy(false);
    }
  };

  const onArchive = async () => {
    setBusy(true);
    try {
      await bulkArchiveCrmLeads(ids, { expected_versions: versions }, workspaceId);
      setMessage(`Archived ${ids.length} lead(s).`);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Archive failed");
    } finally {
      setBusy(false);
    }
  };

  const onNurture = async () => {
    setBusy(true);
    try {
      await createCrmWorkflow(
        {
          name: `Bulk nurture ${ids.length}`,
          meta: { lead_ids: ids, source: "leads_grid_bulk" },
        },
        workspaceId,
      );
      await runPatch({ stage: "enrolled", pipeline_stage: "enrolled" });
      setMessage("Nurture workflow requested for selection.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nurture failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={1} sx={{ mb: 1, p: 1.5, border: 1, borderColor: "divider", borderRadius: 1 }}>
      <Typography variant="body2">{selected.length} selected</Typography>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {message ? <Alert severity="info">{message}</Alert> : null}
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap alignItems="center">
        <TextField size="small" label="Tag" value={tag} onChange={(e) => setTag(e.target.value)} />
        <Button size="small" disabled={busy || !tag.trim()} onClick={() => void runPatch({}, { tags_add: [tag.trim()] })}>
          Add tag
        </Button>
        <TextField size="small" label="Owner agent" value={owner} onChange={(e) => setOwner(e.target.value)} />
        <Button
          size="small"
          disabled={busy || !owner.trim()}
          onClick={() => void runPatch({ owner_agent_id: owner.trim(), assigned_agent: owner.trim() })}
        >
          Set owner
        </Button>
        <TextField size="small" label="Stage" value={stage} onChange={(e) => setStage(e.target.value)} />
        <Button size="small" disabled={busy || !stage.trim()} onClick={() => void onStage()}>
          Set stage
        </Button>
        <TextField size="small" label="Priority" value={priority} onChange={(e) => setPriority(e.target.value)} />
        <Button size="small" disabled={busy || !priority.trim()} onClick={() => void runPatch({ priority: priority.trim() })}>
          Set priority
        </Button>
        <TextField size="small" label="List id" value={listId} onChange={(e) => setListId(e.target.value)} />
        <Button
          size="small"
          disabled={busy || !listId.trim()}
          onClick={() => void runPatch({}, { add_to_list_id: listId.trim() })}
        >
          Add to list
        </Button>
        <TextField size="small" label="Campaign id" value={campaignId} onChange={(e) => setCampaignId(e.target.value)} />
        <Button
          size="small"
          disabled={busy || !campaignId.trim()}
          onClick={() => void runPatch({ campaign_id: campaignId.trim() })}
        >
          Propose campaign
        </Button>
        <Button size="small" disabled={busy} onClick={() => void onNurture()}>
          Nurture
        </Button>
        <Button size="small" disabled={busy} onClick={() => void onExport("xlsx")}>
          Export XLSX
        </Button>
        <Button size="small" disabled={busy} onClick={() => void onExport("csv")}>
          Export CSV
        </Button>
        <Button size="small" color="warning" disabled={busy} onClick={() => void onArchive()}>
          Archive
        </Button>
      </Stack>

      <Dialog open={Boolean(softWall?.approvalId)} onClose={() => setSoftWall(null)}>
        <DialogTitle>Soft Wall required</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            This bulk stage or campaign change needs Soft Wall approval before it can apply.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSoftWall(null)}>Cancel</Button>
          <Button variant="contained" disabled={busy} onClick={() => void approveAndRetry()}>
            Approve and apply
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
