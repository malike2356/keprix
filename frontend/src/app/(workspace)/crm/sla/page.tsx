"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { CRM_WORKSPACE } from "@/components/crm/types";
import {
  assignCrmOwner,
  createCrmTeam,
  fetchCrmSlaInbox,
  fetchCrmTeams,
} from "@/lib/crm-api";

type InboxRow = Record<string, unknown> & {
  id?: string;
  entity_type?: string;
  label?: string;
  owner_user_id?: string | null;
  sla_due_at?: string | null;
  stage?: string;
};

function recordHref(row: InboxRow): string {
  const et = String(row.entity_type || "lead");
  const id = String(row.id || "");
  const map: Record<string, string> = {
    lead: `/crm/leads/${id}`,
    contact: `/crm/contacts/${id}`,
    account: `/crm/accounts/${id}`,
    deal: `/crm/deals/${id}`,
  };
  return map[et] || `/crm/leads/${id}`;
}

function Bucket({
  title,
  rows,
  empty,
  actionLabel,
  onAction,
}: {
  title: string;
  rows: InboxRow[];
  empty: string;
  actionLabel?: string;
  onAction?: (row: InboxRow) => void;
}) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" gutterBottom>
          {title} ({rows.length})
        </Typography>
        {rows.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {empty}
          </Typography>
        ) : (
          <Stack spacing={1}>
            {rows.slice(0, 40).map((row) => (
              <Stack
                key={`${row.entity_type}-${row.id}`}
                direction={{ xs: "column", md: "row" }}
                spacing={1}
                justifyContent="space-between"
                alignItems={{ md: "center" }}
                sx={{ borderBottom: "1px solid", borderColor: "divider", pb: 1 }}
              >
                <Stack spacing={0.25}>
                  <Typography variant="body2">{String(row.label || row.id)}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {String(row.entity_type)} · stage {String(row.stage || "-")} · owner{" "}
                    {String(row.owner_user_id || "unassigned")} · SLA {String(row.sla_due_at || "-")}
                  </Typography>
                </Stack>
                <Stack direction="row" spacing={1}>
                  <Button size="small" component="a" href={recordHref(row)}>
                    Open
                  </Button>
                  {actionLabel && onAction ? (
                    <Button size="small" variant="contained" onClick={() => onAction(row)}>
                      {actionLabel}
                    </Button>
                  ) : null}
                </Stack>
              </Stack>
            ))}
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}

export default function CrmSlaPage() {
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [teamName, setTeamName] = React.useState("SDR team");
  const [membersRaw, setMembersRaw] = React.useState("alice,bob");
  const [selectedTeam, setSelectedTeam] = React.useState("");

  const inbox = useSWR(["crm-sla-inbox", CRM_WORKSPACE], () => fetchCrmSlaInbox(CRM_WORKSPACE));
  const teams = useSWR(["crm-teams", CRM_WORKSPACE], () => fetchCrmTeams(CRM_WORKSPACE));

  const refresh = async () => {
    await Promise.all([inbox.mutate(), teams.mutate()]);
  };

  const createTeam = async () => {
    setError(null);
    try {
      const members = membersRaw
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const res = await createCrmTeam({ name: teamName.trim(), member_user_ids: members }, CRM_WORKSPACE);
      setMessage(`Team ${res.team.name} created`);
      setSelectedTeam(res.team.id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create team failed");
    }
  };

  const claim = async (row: InboxRow) => {
    setError(null);
    try {
      const res = await assignCrmOwner(
        {
          entity_type: String(row.entity_type || "lead"),
          entity_id: String(row.id),
          mode: "claim",
          sla_hours: 24,
        },
        CRM_WORKSPACE,
      );
      if (res.blocked) {
        setError("Soft Wall approval required for this reassignment. Approve on /crm then retry.");
        return;
      }
      if (!res.ok) {
        setError(String(res.error || "Claim failed"));
        return;
      }
      setMessage(`Claimed ${String(row.label || row.id)}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Claim failed");
    }
  };

  const roundRobin = async (row: InboxRow) => {
    setError(null);
    if (!selectedTeam) {
      setError("Select or create a team first");
      return;
    }
    try {
      const res = await assignCrmOwner(
        {
          entity_type: String(row.entity_type || "lead"),
          entity_id: String(row.id),
          team_id: selectedTeam,
          mode: "round_robin",
          sla_hours: 24,
        },
        CRM_WORKSPACE,
      );
      if (res.blocked) {
        setError("Soft Wall approval required (paying/customer deal reassign).");
        return;
      }
      if (!res.ok) {
        setError(String(res.error || "Round-robin assign failed"));
        return;
      }
      setMessage(`Assigned ${String(row.label || row.id)} via round-robin`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Assign failed");
    }
  };

  const data = inbox.data;
  const teamItems = teams.data?.items || [];

  return (
    <Stack spacing={2}>
      <Stack spacing={0.5}>
        <Typography variant="h5">SLA inbox</Typography>
        <Typography variant="body2" color="text.secondary">
          Overdue, due today, and unassigned queue. Claim from queue or assign round-robin. Soft locks warn on
          concurrent edits when opening records. Paying deal reassign is Soft Wall gated.
        </Typography>
      </Stack>

      {error ? <Alert severity="error">{error}</Alert> : null}
      {message ? <Alert severity="success">{message}</Alert> : null}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Teams
          </Typography>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ mb: 1.5 }}>
            <TextField
              size="small"
              label="Team name"
              value={teamName}
              onChange={(e) => setTeamName(e.target.value)}
            />
            <TextField
              size="small"
              label="Members (comma-separated user ids)"
              value={membersRaw}
              onChange={(e) => setMembersRaw(e.target.value)}
              sx={{ minWidth: 280 }}
            />
            <Button variant="contained" onClick={() => void createTeam()} disabled={!teamName.trim()}>
              Create team
            </Button>
          </Stack>
          {teamItems.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No teams yet.
            </Typography>
          ) : (
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {teamItems.map((t) => (
                <Button
                  key={t.id}
                  size="small"
                  variant={selectedTeam === t.id ? "contained" : "outlined"}
                  onClick={() => setSelectedTeam(t.id)}
                >
                  {t.name} ({(t.member_user_ids || []).length})
                </Button>
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>

      {inbox.isLoading ? (
        <Typography color="text.secondary">Loading SLA inbox...</Typography>
      ) : (
        <>
          <Bucket
            title="Overdue"
            rows={(data?.overdue || []) as InboxRow[]}
            empty="No overdue SLA items."
            actionLabel={selectedTeam ? "Round-robin" : undefined}
            onAction={selectedTeam ? (row) => void roundRobin(row) : undefined}
          />
          <Bucket
            title="Due today"
            rows={(data?.due_today || []) as InboxRow[]}
            empty="Nothing due today."
            actionLabel={selectedTeam ? "Round-robin" : undefined}
            onAction={selectedTeam ? (row) => void roundRobin(row) : undefined}
          />
          <Bucket
            title="Unassigned"
            rows={(data?.unassigned || []) as InboxRow[]}
            empty="No unassigned records."
            actionLabel="Claim"
            onAction={(row) => void claim(row)}
          />
        </>
      )}

      <Typography variant="caption" color="text.secondary">
        Counts: overdue {data?.counts?.overdue ?? 0}, due today {data?.counts?.due_today ?? 0}, unassigned{" "}
        {data?.counts?.unassigned ?? 0}. Soft Wall approvals stay on /crm.
      </Typography>
    </Stack>
  );
}
