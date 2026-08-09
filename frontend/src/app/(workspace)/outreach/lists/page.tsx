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
import * as React from "react";
import useSWR from "swr";
import { leadIdsOf } from "@/components/outreach/types";
import {
  addLeadsToOutreachList,
  createOutreachList,
  enrollOutreachList,
  fetchOutreachLeads,
  fetchOutreachLists,
  fetchOutreachSequences,
  patchOutreachList,
  preflightOutreachListEnroll,
} from "@/lib/outreach-api";

const WORKSPACE = "default";

export default function OutreachListsPage() {
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [drafts, setDrafts] = React.useState<Record<string, { name: string; description: string; leadIds: string }>>({});
  const [enrollListId, setEnrollListId] = React.useState<string | null>(null);
  const [sequenceId, setSequenceId] = React.useState("");
  const [preflight, setPreflight] = React.useState<Awaited<ReturnType<typeof preflightOutreachListEnroll>> | null>(null);

  const lists = useSWR(["outreach-lists", WORKSPACE], () => fetchOutreachLists(WORKSPACE));
  const leads = useSWR(["outreach-leads", WORKSPACE], () => fetchOutreachLeads(WORKSPACE));
  const sequences = useSWR(["outreach-sequences", WORKSPACE], () => fetchOutreachSequences(WORKSPACE));

  React.useEffect(() => {
    const next: Record<string, { name: string; description: string; leadIds: string }> = {};
    for (const list of lists.data?.lists ?? []) {
      next[list.id] = drafts[list.id] ?? {
        name: list.name,
        description: list.description ?? "",
        leadIds: leadIdsOf(list).join(", "),
      };
    }
    setDrafts(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lists.data]);

  React.useEffect(() => {
    const first = sequences.data?.sequences?.[0]?.id;
    if (!sequenceId && first) setSequenceId(first);
  }, [sequences.data, sequenceId]);

  const onCreate = async () => {
    setBusy(true);
    setError(null);
    try {
      if (!name.trim()) throw new Error("List name is required");
      const seedIds = (leads.data?.leads ?? []).slice(0, 25).map((l) => l.id);
      await createOutreachList(
        { name: name.trim(), description: description.trim() || undefined, lead_ids: seedIds },
        WORKSPACE,
      );
      setName("");
      setDescription("");
      setMessage("List created");
      await lists.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create list");
    } finally {
      setBusy(false);
    }
  };

  const onSave = async (listId: string) => {
    const draft = drafts[listId];
    if (!draft) return;
    setBusy(true);
    setError(null);
    try {
      const leadIds = draft.leadIds.split(",").map((item) => item.trim()).filter(Boolean);
      await patchOutreachList(listId, { name: draft.name, description: draft.description, lead_ids: leadIds }, WORKSPACE);
      setMessage("List saved. Prior Soft Wall enroll approvals are invalid if membership changed.");
      await lists.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save list");
    } finally {
      setBusy(false);
    }
  };

  const onAddRecent = async (listId: string) => {
    setBusy(true);
    setError(null);
    try {
      const leadIds = (leads.data?.leads ?? []).slice(0, 25).map((l) => l.id);
      await addLeadsToOutreachList(listId, leadIds, WORKSPACE);
      setMessage("Recent leads added");
      await lists.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add leads");
    } finally {
      setBusy(false);
    }
  };

  const openEnroll = async (listId: string) => {
    setEnrollListId(listId);
    setPreflight(null);
    setError(null);
    if (!sequenceId) return;
    setBusy(true);
    try {
      setPreflight(await preflightOutreachListEnroll(listId, { sequence_id: sequenceId }, WORKSPACE));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preflight failed");
    } finally {
      setBusy(false);
    }
  };

  const runPreflight = async () => {
    if (!enrollListId || !sequenceId) return;
    setBusy(true);
    setError(null);
    try {
      setPreflight(await preflightOutreachListEnroll(enrollListId, { sequence_id: sequenceId }, WORKSPACE));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preflight failed");
    } finally {
      setBusy(false);
    }
  };

  const confirmEnroll = async () => {
    if (!enrollListId || !sequenceId || !preflight) return;
    setBusy(true);
    setError(null);
    try {
      const result = await enrollOutreachList(
        enrollListId,
        { sequence_id: sequenceId, audience_hash: preflight.audience_hash },
        WORKSPACE,
      );
      if (result.blocked) {
        setMessage("Soft Wall approval created for list enroll. Review Approvals, then retry with approval.");
      } else {
        setMessage(
          `Enrolled ${result.enrolled_count ?? 0} eligible leads. Skipped suppressed=${result.skipped?.suppressed ?? 0}, deny=${result.skipped?.contactability_deny ?? 0}.`,
        );
      }
      setEnrollListId(null);
      setPreflight(null);
      await lists.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Enroll failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2}>
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

      <Typography variant="body2" color="text.secondary">
        Soft Wall lists enroll into sequences with a preflight Soft Wall gate. Suppressed and contactability-deny
        members are skipped with fix links.
      </Typography>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            New list
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <TextField size="small" fullWidth label="List name" value={name} onChange={(e) => setName(e.target.value)} />
            <TextField
              size="small"
              fullWidth
              label="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <Button size="small" variant="contained" disabled={busy} onClick={() => void onCreate()}>
              Create
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {lists.isLoading && !lists.data ? (
        <Typography color="text.secondary">Loading lists...</Typography>
      ) : (lists.data?.lists ?? []).length === 0 ? (
        <Typography color="text.secondary">No lists yet.</Typography>
      ) : (
        <Stack spacing={1.5}>
          {(lists.data?.lists ?? []).map((list) => {
            const draft = drafts[list.id];
            return (
              <Card key={list.id} variant="outlined">
                <CardContent>
                  <Typography variant="caption" color="text.secondary">
                    {leadIdsOf(list).length} member(s)
                  </Typography>
                  <Stack spacing={1.5} sx={{ mt: 1 }}>
                    <TextField
                      size="small"
                      label="Name"
                      value={draft?.name ?? list.name}
                      onChange={(e) =>
                        setDrafts((current) => ({
                          ...current,
                          [list.id]: {
                            ...(current[list.id] ?? { name: "", description: "", leadIds: "" }),
                            name: e.target.value,
                          },
                        }))
                      }
                    />
                    <TextField
                      size="small"
                      label="Description"
                      value={draft?.description ?? ""}
                      onChange={(e) =>
                        setDrafts((current) => ({
                          ...current,
                          [list.id]: {
                            ...(current[list.id] ?? { name: list.name, description: "", leadIds: "" }),
                            description: e.target.value,
                          },
                        }))
                      }
                    />
                    <TextField
                      size="small"
                      label="Lead IDs (comma-separated)"
                      value={draft?.leadIds ?? ""}
                      onChange={(e) =>
                        setDrafts((current) => ({
                          ...current,
                          [list.id]: {
                            ...(current[list.id] ?? { name: list.name, description: "", leadIds: "" }),
                            leadIds: e.target.value,
                          },
                        }))
                      }
                    />
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      <Button size="small" variant="contained" disabled={busy} onClick={() => void onSave(list.id)}>
                        Save
                      </Button>
                      <Button size="small" variant="outlined" disabled={busy} onClick={() => void onAddRecent(list.id)}>
                        Add recent leads
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        color="secondary"
                        disabled={busy}
                        onClick={() => void openEnroll(list.id)}
                      >
                        Soft Wall enroll
                      </Button>
                    </Stack>
                  </Stack>
                </CardContent>
              </Card>
            );
          })}
        </Stack>
      )}

      <Dialog open={Boolean(enrollListId)} onClose={() => setEnrollListId(null)} fullWidth maxWidth="sm">
        <DialogTitle>Soft Wall list enroll preflight</DialogTitle>
        <DialogContent>
          <Stack spacing={1.5} sx={{ mt: 1 }}>
            <FormControl size="small" fullWidth>
              <InputLabel id="seq">Sequence</InputLabel>
              <Select labelId="seq" label="Sequence" value={sequenceId} onChange={(e) => setSequenceId(String(e.target.value))}>
                {(sequences.data?.sequences ?? []).map((seq) => (
                  <MenuItem key={seq.id} value={seq.id}>
                    {seq.name || seq.id}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button size="small" variant="outlined" disabled={busy || !sequenceId} onClick={() => void runPreflight()}>
              Refresh preflight
            </Button>
            {preflight ? (
              <>
                <Typography variant="body2">
                  Eligible {preflight.counts.eligible} / total {preflight.counts.total}. Suppressed{" "}
                  {preflight.counts.suppressed}. Contactability deny {preflight.counts.contactability_deny}. Duplicate{" "}
                  {preflight.counts.duplicate}. Ambiguous {preflight.counts.ambiguous}. Ineligible{" "}
                  {preflight.counts.ineligible}.
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  audience_hash={preflight.audience_hash}. {preflight.note}
                </Typography>
                {(preflight.suppressed?.length || 0) > 0 ? (
                  <Button component="a" href="/outreach/suppressions" size="small">
                    Fix suppressions
                  </Button>
                ) : null}
                {(preflight.contactability_deny?.length || 0) > 0 ? (
                  <Button component="a" href="/outreach/contactability" size="small">
                    Fix contactability
                  </Button>
                ) : null}
              </>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Run preflight to see eligible vs skipped counts before Soft Wall approve.
              </Typography>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEnrollListId(null)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={busy || !preflight || (preflight.counts.eligible ?? 0) < 1}
            onClick={() => void confirmEnroll()}
          >
            Soft Wall enroll eligible
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
