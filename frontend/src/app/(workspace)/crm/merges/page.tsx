"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { applyCrmMerge, fetchCrmMerges, rejectCrmMerge } from "@/lib/crm-api";

/**
 * CRM Soft Wall identity merges. Uses /api/crm/merges (same store Soft Wall
 * outreach reuses). Consent is never auto-unioned across people.
 */
export default function CrmMergesPage() {
  const { data, error, mutate, isLoading } = useSWR(["crm-merges", CRM_WORKSPACE], () =>
    fetchCrmMerges(CRM_WORKSPACE),
  );
  const [busyId, setBusyId] = React.useState<string | null>(null);
  const [msg, setMsg] = React.useState<string | null>(null);
  const [err, setErr] = React.useState<string | null>(null);

  const items = data?.items ?? [];

  const act = async (id: string, action: "apply" | "reject") => {
    setBusyId(id);
    setErr(null);
    try {
      if (action === "apply") {
        const result = await applyCrmMerge(id, {}, CRM_WORKSPACE);
        if (result.blocked) setMsg("Soft Wall approval required to merge. Consent is not auto-unioned.");
        else setMsg("Merge applied");
      } else {
        await rejectCrmMerge(id, "operator_rejected", CRM_WORKSPACE);
        setMsg("Suggestion rejected; both records kept");
      }
      await mutate();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Stack spacing={2}>
      {error || err ? (
        <Alert severity="error" onClose={() => setErr(null)}>
          {error instanceof Error ? error.message : err}
        </Alert>
      ) : null}
      {msg ? (
        <Alert severity="success" onClose={() => setMsg(null)}>
          {msg}
        </Alert>
      ) : null}

      <Typography variant="body2" color="text.secondary">
        Fuzzy identity matches wait here. Never silent merge. Consent and suppression transfer
        require an explicit Soft Wall step (default deny). Soft merges remain reversible in merge
        history.
      </Typography>

      {!isLoading && items.length === 0 ? (
        <EmptyState
          title="No pending merge suggestions"
          description="When fuzzy matches appear, review provenance side-by-side before Soft Wall apply."
        />
      ) : null}

      {items.map((row) => {
        const diff =
          typeof row.field_diff === "object" && row.field_diff
            ? row.field_diff
            : (() => {
                try {
                  return JSON.parse(String(row.field_diff_json || "{}"));
                } catch {
                  return {};
                }
              })();
        return (
          <Paper key={String(row.id)} variant="outlined" sx={{ p: 2 }}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1} justifyContent="space-between">
              <Stack spacing={0.5} sx={{ minWidth: 0, flex: 1 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                  {String(row.entity_type)} {String(row.left_id)} / {String(row.right_id)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Score: {String(row.score ?? "-")}
                </Typography>
                <Stack spacing={0.5}>
                  <Typography variant="caption" color="text.secondary">
                    Keys
                  </Typography>
                  <StructuredDataView value={row.match_keys || []} />
                </Stack>
                <Typography variant="body2">{String(row.explanation || "")}</Typography>
                <Stack sx={{ p: 1, bgcolor: "action.hover", overflow: "auto", maxHeight: 180, borderRadius: 1 }}>
                  <StructuredDataView value={diff} />
                </Stack>
              </Stack>
              <Stack direction="row" spacing={1} alignItems="flex-start">
                <Button
                  variant="contained"
                  size="small"
                  disabled={busyId === row.id}
                  onClick={() => void act(String(row.id), "apply")}
                >
                  Soft Wall apply
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  disabled={busyId === row.id}
                  onClick={() => void act(String(row.id), "reject")}
                >
                  Reject
                </Button>
                <Button component="a" href="/crm" size="small">
                  Soft Wall panel
                </Button>
              </Stack>
            </Stack>
          </Paper>
        );
      })}
    </Stack>
  );
}
