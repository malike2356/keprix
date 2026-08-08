"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import CrmSoftWallPanel from "@/components/crm/CrmSoftWallPanel";
import { CRM_WORKSPACE, displayName, stageLabel } from "@/components/crm/types";
import {
  addCrmListMember,
  enrollCrmList,
  fetchCrmKillSwitches,
  fetchCrmListDetail,
  patchCrmRecord,
  preflightCrmListEnroll,
} from "@/lib/crm-api";
import { fetchOutreachSequences } from "@/lib/outreach-api";

type Preflight = {
  counts?: Record<string, number>;
  audience_hash?: string;
  content_hash?: string;
  contactability_deny?: Array<{ reason?: string }>;
  suppressed?: unknown[];
  kill_reasons?: string[];
  deep_links?: Record<string, string>;
};

export default function CrmListDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [memberType, setMemberType] = React.useState<"lead" | "contact">("lead");
  const [memberId, setMemberId] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [enrollOpen, setEnrollOpen] = React.useState(false);
  const [sequenceId, setSequenceId] = React.useState("");
  const [preflight, setPreflight] = React.useState<Preflight | null>(null);
  const [approvalId, setApprovalId] = React.useState<string | null>(null);

  const detail = useSWR(id ? ["crm-list", CRM_WORKSPACE, id] : null, () =>
    fetchCrmListDetail(id, CRM_WORKSPACE),
  );
  const sequences = useSWR(["outreach-sequences", CRM_WORKSPACE], () =>
    fetchOutreachSequences(CRM_WORKSPACE).catch(() => ({ sequences: [] as Array<{ id: string; name?: string }> })),
  );
  const kills = useSWR(["crm-kills", CRM_WORKSPACE], () => fetchCrmKillSwitches(CRM_WORKSPACE));

  React.useEffect(() => {
    const list = detail.data?.list;
    if (!list) return;
    setName(String(list.name || ""));
    setDescription(String(list.description || ""));
  }, [detail.data]);

  if (detail.isLoading && !detail.data) {
    return <Typography color="text.secondary">Loading list...</Typography>;
  }

  if (!detail.data?.list) {
    return (
      <Typography color="text.secondary">
        List not found.{" "}
        <Typography component={Link} href="/crm/lists" color="primary" sx={{ textDecoration: "underline" }}>
          Back to lists
        </Typography>
      </Typography>
    );
  }

  const list = detail.data.list;
  const members = detail.data.members ?? [];
  const killOn = (kills.data?.items || []).some((k) => k.enabled && String(k.scope) === "workspace");
  const seqItems = (sequences.data as { sequences?: Array<{ id: string; name?: string }> } | undefined)?.sequences
    || (sequences.data as { items?: Array<{ id: string; name?: string }> } | undefined)?.items
    || [];

  const onSave = async () => {
    setBusy(true);
    setError(null);
    try {
      await patchCrmRecord(
        "lists",
        id,
        {
          name: name.trim(),
          description: description.trim() || null,
          expected_version: list.version,
        },
        CRM_WORKSPACE,
      );
      setMessage("List saved");
      await detail.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save list");
    } finally {
      setBusy(false);
    }
  };

  const onAddMember = async () => {
    setBusy(true);
    setError(null);
    try {
      if (!memberId.trim()) throw new Error("Member id is required");
      await addCrmListMember(
        id,
        { member_type: memberType, member_id: memberId.trim() },
        CRM_WORKSPACE,
      );
      setMemberId("");
      setMessage("Member added");
      await detail.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add member");
    } finally {
      setBusy(false);
    }
  };

  const runPreflight = async () => {
    setBusy(true);
    setError(null);
    try {
      if (!sequenceId) throw new Error("Pick a Soft Wall sequence");
      const report = (await preflightCrmListEnroll(
        id,
        { sequence_id: sequenceId },
        CRM_WORKSPACE,
      )) as Preflight;
      setPreflight(report);
      setMessage("Preflight ready. Review counts before Soft Wall submit.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preflight failed");
    } finally {
      setBusy(false);
    }
  };

  const submitEnroll = async () => {
    setBusy(true);
    setError(null);
    try {
      if (!sequenceId || !preflight?.audience_hash) throw new Error("Run preflight first");
      const result = (await enrollCrmList(
        id,
        {
          sequence_id: sequenceId,
          audience_hash: preflight.audience_hash,
          content_hash: preflight.content_hash,
          approval_id: approvalId || undefined,
          require_soft_wall: true,
        },
        CRM_WORKSPACE,
      )) as {
        blocked?: boolean;
        approval?: { id?: string };
        enrolled_count?: number;
        error_code?: string;
        message?: string;
      };
      if (result.blocked) {
        setApprovalId(String(result.approval?.id || ""));
        setMessage(
          result.error_code === "soft_wall_required"
            ? `Soft Wall pending: ${result.approval?.id}. Approve then submit again.`
            : result.message || result.error_code || "Blocked",
        );
        return;
      }
      setMessage(`Enrolled ${result.enrolled_count || 0} member(s)`);
      setEnrollOpen(false);
      setPreflight(null);
      await detail.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Enroll failed");
    } finally {
      setBusy(false);
    }
  };

  const counts = preflight?.counts || {};

  return (
    <Stack spacing={2} sx={{ maxWidth: 880 }}>
      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Button size="small" component={Link} href="/crm/lists" sx={{ alignSelf: "flex-start" }}>
        All lists
      </Button>

      <Card variant="outlined">
        <CardContent>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            <Typography variant="h5">{displayName(list)}</Typography>
            {killOn ? (
              <Typography variant="caption" color="error.main">
                Kill switch ON
              </Typography>
            ) : (
              <Typography variant="caption" color="text.secondary">
                Kill switch off
              </Typography>
            )}
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {stageLabel(list.stage || list.status)}
            {list.source ? ` · ${list.source}` : ""}
            {` · ${members.length} member(s)`}
          </Typography>
          <Stack spacing={1.5} sx={{ mt: 2 }}>
            <TextField size="small" label="Name" value={name} onChange={(e) => setName(e.target.value)} />
            <TextField
              size="small"
              label="Description"
              multiline
              minRows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Button size="small" variant="contained" disabled={busy} onClick={() => void onSave()}>
                Save
              </Button>
              <Button size="small" variant="outlined" disabled={busy} onClick={() => setEnrollOpen(true)}>
                Enroll
              </Button>
              <Button size="small" component={Link} href="/crm/deliverability">
                Sender readiness
              </Button>
              <Button size="small" component={Link} href="/crm/settings">
                Kill switches
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Members
          </Typography>
          {members.length === 0 ? (
            <Typography color="text.secondary" sx={{ mb: 1.5 }}>
              No members yet. Add a lead or contact id below.
            </Typography>
          ) : (
            <Stack spacing={1} sx={{ mb: 1.5 }}>
              {members.map((member) => (
                <Typography key={member.id} variant="body2" color="text.secondary">
                  {String(member.member_type || "member")} · {String(member.member_id || member.id)}
                  {member.stage ? ` · ${stageLabel(String(member.stage))}` : ""}
                </Typography>
              ))}
            </Stack>
          )}
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel id="member-type">Type</InputLabel>
              <Select
                labelId="member-type"
                label="Type"
                value={memberType}
                onChange={(e) => setMemberType(e.target.value as "lead" | "contact")}
              >
                <MenuItem value="lead">Lead</MenuItem>
                <MenuItem value="contact">Contact</MenuItem>
              </Select>
            </FormControl>
            <TextField
              size="small"
              fullWidth
              label="Member id"
              value={memberId}
              onChange={(e) => setMemberId(e.target.value)}
            />
            <Button size="small" variant="outlined" disabled={busy} onClick={() => void onAddMember()}>
              Add
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <CrmSoftWallPanel title="Soft Wall for this workspace" />

      <Dialog open={enrollOpen} onClose={() => setEnrollOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Enroll list via Soft Wall</DialogTitle>
        <DialogContent>
          <Stack spacing={1.5} sx={{ mt: 1 }}>
            <FormControl size="small" fullWidth>
              <InputLabel id="seq">Sequence</InputLabel>
              <Select
                labelId="seq"
                label="Sequence"
                value={sequenceId}
                onChange={(e) => {
                  setSequenceId(String(e.target.value));
                  setPreflight(null);
                }}
              >
                {seqItems.map((s) => (
                  <MenuItem key={s.id} value={s.id}>
                    {s.name || s.id}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            {preflight ? (
              <Alert severity="info">
                Eligible {counts.eligible ?? 0} · Suppressed {counts.suppressed ?? 0} · Contactability deny{" "}
                {counts.contactability_deny ?? 0} · Duplicate {counts.duplicate ?? 0} · Ambiguous{" "}
                {counts.ambiguous ?? 0} · Ineligible {counts.ineligible ?? 0}
                {(preflight.contactability_deny?.length || 0) > 0 ? (
                  <>
                    {" "}
                    <Link href="/crm/contactability">Open contactability</Link>
                  </>
                ) : null}
                {(preflight.suppressed as unknown[] | undefined)?.length ? (
                  <>
                    {" "}
                    <Link href="/crm/suppressions">Open suppressions</Link>
                  </>
                ) : null}
              </Alert>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Preflight shows counts in this modal before Soft Wall submit (not API-only).
              </Typography>
            )}
            {approvalId ? (
              <TextField
                size="small"
                label="Approval id (after Soft Wall approve)"
                value={approvalId}
                onChange={(e) => setApprovalId(e.target.value)}
              />
            ) : null}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEnrollOpen(false)}>Close</Button>
          <Button disabled={busy || !sequenceId} onClick={() => void runPreflight()}>
            Preflight
          </Button>
          <Button variant="contained" disabled={busy || !preflight} onClick={() => void submitEnroll()}>
            Soft Wall enroll
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
