"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import type { OutreachSequence } from "@/components/outreach/types";
import {
  createOutreachSequence,
  fetchOutreachSequences,
  patchOutreachSequence,
} from "@/lib/outreach-api";

const WORKSPACE = "default";

type StepDraft = {
  order: string;
  label: string;
  channel: string;
  subject: string;
  body: string;
  delay_hours: string;
};

type SeqDraft = {
  name: string;
  description: string;
  channel_default: string;
  stop_on_reply: boolean;
  stop_on_booking: boolean;
  stop_on_unsubscribe: boolean;
  steps: StepDraft[];
};

function stepsOf(sequence: OutreachSequence): StepDraft[] {
  return (sequence.steps ?? []).map((step, index) => ({
    order: String(step.order ?? index),
    label: step.label ?? `Step ${index + 1}`,
    channel: step.channel ?? "email",
    subject: step.subject ?? "",
    body: step.body ?? "",
    delay_hours: String(step.delay_hours ?? step.delayHours ?? 0),
  }));
}

function toDraft(sequence: OutreachSequence): SeqDraft {
  return {
    name: sequence.name,
    description: sequence.description ?? "",
    channel_default: sequence.channel_default ?? "email",
    stop_on_reply: sequence.stop_on_reply ?? sequence.stopOnReply ?? true,
    stop_on_booking: sequence.stop_on_booking ?? sequence.stopOnBooking ?? true,
    stop_on_unsubscribe: sequence.stop_on_unsubscribe ?? sequence.stopOnUnsubscribe ?? true,
    steps: stepsOf(sequence),
  };
}

function blankDraft(): SeqDraft {
  return {
    name: "New sequence",
    description: "",
    channel_default: "email",
    stop_on_reply: true,
    stop_on_booking: true,
    stop_on_unsubscribe: true,
    steps: [
      {
        order: "0",
        label: "First touch",
        channel: "email",
        subject: "Quick idea for {{company}}",
        body: "Hi {{name}},\n\nI noticed {{company}} and thought this might help.\n\nBest",
        delay_hours: "0",
      },
    ],
  };
}

function toPayloadSteps(steps: StepDraft[]) {
  return steps.map((step) => ({
    order: Number(step.order) || 0,
    label: step.label,
    channel: step.channel,
    subject: step.subject,
    body: step.body,
    delay_hours: Number(step.delay_hours) || 0,
  }));
}

export default function OutreachSequencesPage() {
  const [newDraft, setNewDraft] = React.useState<SeqDraft>(blankDraft());
  const [drafts, setDrafts] = React.useState<Record<string, SeqDraft>>({});
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const sequences = useSWR(["outreach-sequences", WORKSPACE], () => fetchOutreachSequences(WORKSPACE));

  React.useEffect(() => {
    const next: Record<string, SeqDraft> = {};
    for (const sequence of sequences.data?.sequences ?? []) {
      next[sequence.id] = drafts[sequence.id] ?? toDraft(sequence);
    }
    setDrafts(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sequences.data]);

  const onCreate = async () => {
    setBusy(true);
    setError(null);
    try {
      if (!newDraft.name.trim()) throw new Error("Sequence name is required");
      if (!newDraft.steps.length) throw new Error("Add at least one step");
      await createOutreachSequence(
        {
          name: newDraft.name.trim(),
          description: newDraft.description.trim() || undefined,
          channel_default: newDraft.channel_default,
          stop_on_reply: newDraft.stop_on_reply,
          stop_on_booking: newDraft.stop_on_booking,
          stop_on_unsubscribe: newDraft.stop_on_unsubscribe,
          steps: toPayloadSteps(newDraft.steps),
        },
        WORKSPACE,
      );
      setNewDraft(blankDraft());
      setMessage("Sequence created");
      await sequences.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create sequence");
    } finally {
      setBusy(false);
    }
  };

  const onSave = async (sequenceId: string) => {
    const draft = drafts[sequenceId];
    if (!draft) return;
    setBusy(true);
    setError(null);
    try {
      await patchOutreachSequence(
        sequenceId,
        {
          name: draft.name,
          description: draft.description,
          channel_default: draft.channel_default,
          stop_on_reply: draft.stop_on_reply,
          stop_on_booking: draft.stop_on_booking,
          stop_on_unsubscribe: draft.stop_on_unsubscribe,
          steps: toPayloadSteps(draft.steps),
        },
        WORKSPACE,
      );
      setMessage("Sequence saved");
      await sequences.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save sequence");
    } finally {
      setBusy(false);
    }
  };

  const renderStepEditor = (
    steps: StepDraft[],
    onChange: (next: StepDraft[]) => void,
  ) => (
    <Stack spacing={1.5}>
      {steps.map((step, index) => (
        <Card key={index} variant="outlined">
          <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
            <Stack spacing={1}>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                <TextField
                  size="small"
                  label="Order"
                  value={step.order}
                  onChange={(e) => {
                    const next = [...steps];
                    next[index] = { ...step, order: e.target.value };
                    onChange(next);
                  }}
                  sx={{ width: 100 }}
                />
                <TextField
                  size="small"
                  fullWidth
                  label="Label"
                  value={step.label}
                  onChange={(e) => {
                    const next = [...steps];
                    next[index] = { ...step, label: e.target.value };
                    onChange(next);
                  }}
                />
                <TextField
                  size="small"
                  label="Delay hours"
                  value={step.delay_hours}
                  onChange={(e) => {
                    const next = [...steps];
                    next[index] = { ...step, delay_hours: e.target.value };
                    onChange(next);
                  }}
                  sx={{ width: 120 }}
                />
              </Stack>
              <TextField
                size="small"
                fullWidth
                label="Subject"
                value={step.subject}
                onChange={(e) => {
                  const next = [...steps];
                  next[index] = { ...step, subject: e.target.value };
                  onChange(next);
                }}
              />
              <TextField
                size="small"
                fullWidth
                multiline
                minRows={3}
                label="Body"
                value={step.body}
                onChange={(e) => {
                  const next = [...steps];
                  next[index] = { ...step, body: e.target.value };
                  onChange(next);
                }}
              />
            </Stack>
          </CardContent>
        </Card>
      ))}
      <Button
        size="small"
        variant="outlined"
        onClick={() =>
          onChange([
            ...steps,
            {
              order: String(steps.length),
              label: `Step ${steps.length + 1}`,
              channel: "email",
              subject: "",
              body: "",
              delay_hours: "24",
            },
          ])
        }
      >
        Add step
      </Button>
    </Stack>
  );

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
        Sequence steps queue through Soft Wall. No mass-send without approval.
      </Typography>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            New sequence
          </Typography>
          <Stack spacing={1.5}>
            <TextField
              size="small"
              label="Name"
              value={newDraft.name}
              onChange={(e) => setNewDraft((d) => ({ ...d, name: e.target.value }))}
            />
            <TextField
              size="small"
              label="Description"
              value={newDraft.description}
              onChange={(e) => setNewDraft((d) => ({ ...d, description: e.target.value }))}
            />
            <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
              <FormControlLabel
                control={
                  <Switch
                    checked={newDraft.stop_on_reply}
                    onChange={(e) => setNewDraft((d) => ({ ...d, stop_on_reply: e.target.checked }))}
                  />
                }
                label="Stop on reply"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={newDraft.stop_on_booking}
                    onChange={(e) => setNewDraft((d) => ({ ...d, stop_on_booking: e.target.checked }))}
                  />
                }
                label="Stop on booking"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={newDraft.stop_on_unsubscribe}
                    onChange={(e) => setNewDraft((d) => ({ ...d, stop_on_unsubscribe: e.target.checked }))}
                  />
                }
                label="Stop on unsubscribe"
              />
            </Stack>
            {renderStepEditor(newDraft.steps, (steps) => setNewDraft((d) => ({ ...d, steps })))}
            <Button size="small" variant="contained" disabled={busy} onClick={() => void onCreate()} sx={{ alignSelf: "flex-start" }}>
              Create sequence
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {sequences.isLoading && !sequences.data ? (
        <Typography color="text.secondary">Loading sequences...</Typography>
      ) : (sequences.data?.sequences ?? []).length === 0 ? (
        <Typography color="text.secondary">No sequences yet.</Typography>
      ) : (
        <Stack spacing={2}>
          {(sequences.data?.sequences ?? []).map((sequence) => {
            const draft = drafts[sequence.id] ?? toDraft(sequence);
            return (
              <Card key={sequence.id} variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" gutterBottom>
                    {sequence.name}
                  </Typography>
                  <Stack spacing={1.5}>
                    <TextField
                      size="small"
                      label="Name"
                      value={draft.name}
                      onChange={(e) => setDrafts((c) => ({ ...c, [sequence.id]: { ...draft, name: e.target.value } }))}
                    />
                    <TextField
                      size="small"
                      label="Description"
                      value={draft.description}
                      onChange={(e) =>
                        setDrafts((c) => ({ ...c, [sequence.id]: { ...draft, description: e.target.value } }))
                      }
                    />
                    <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={draft.stop_on_reply}
                            onChange={(e) =>
                              setDrafts((c) => ({ ...c, [sequence.id]: { ...draft, stop_on_reply: e.target.checked } }))
                            }
                          />
                        }
                        label="Stop on reply"
                      />
                      <FormControlLabel
                        control={
                          <Switch
                            checked={draft.stop_on_booking}
                            onChange={(e) =>
                              setDrafts((c) => ({
                                ...c,
                                [sequence.id]: { ...draft, stop_on_booking: e.target.checked },
                              }))
                            }
                          />
                        }
                        label="Stop on booking"
                      />
                      <FormControlLabel
                        control={
                          <Switch
                            checked={draft.stop_on_unsubscribe}
                            onChange={(e) =>
                              setDrafts((c) => ({
                                ...c,
                                [sequence.id]: { ...draft, stop_on_unsubscribe: e.target.checked },
                              }))
                            }
                          />
                        }
                        label="Stop on unsubscribe"
                      />
                    </Stack>
                    {renderStepEditor(draft.steps, (steps) =>
                      setDrafts((c) => ({ ...c, [sequence.id]: { ...draft, steps } })),
                    )}
                    <Button
                      size="small"
                      variant="contained"
                      disabled={busy}
                      onClick={() => void onSave(sequence.id)}
                      sx={{ alignSelf: "flex-start" }}
                    >
                      Save sequence
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            );
          })}
        </Stack>
      )}
    </Stack>
  );
}
