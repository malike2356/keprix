"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import {
  createCrmActivity,
  createCrmConsent,
  exportCrmSubject,
  fetchCrmActivities,
  offerCrmBooking,
  patchCrmRecord,
} from "@/lib/crm-api";
import {
  CRM_STAGES,
  CRM_WORKSPACE,
  displayName,
  formatTouch,
  primaryEmail,
  singularKind,
  stageLabel,
  type CrmEntityKind,
  type CrmRecord,
} from "@/components/crm/types";

type FieldDef = {
  key: string;
  label: string;
  multiline?: boolean;
};

type CrmDetailEditorProps = {
  kind: CrmEntityKind;
  record: CrmRecord;
  fields: FieldDef[];
  backHref: string;
  backLabel: string;
  onSaved?: (record: CrmRecord) => void;
  workspaceId?: string;
};

function provenanceBadges(record: CrmRecord): Array<{ label: string; hint: string }> {
  const badges: Array<{ label: string; hint: string }> = [];
  if (record.source) badges.push({ label: `source: ${record.source}`, hint: "Record source" });
  if (record.domain_pack) badges.push({ label: `pack: ${record.domain_pack}`, hint: "Domain pack" });
  const scores = record.scores || {};
  const confidence = scores.confidence ?? scores.score;
  if (confidence !== undefined && confidence !== null) {
    badges.push({ label: `confidence: ${String(confidence)}`, hint: "Score confidence" });
  }
  if (record.external_source_id) {
    badges.push({ label: "external id", hint: String(record.external_source_id) });
  }
  if (badges.length === 0) {
    badges.push({ label: "provenance pending", hint: "Field-level provenance API not listed yet" });
  }
  return badges;
}

export function CrmDetailEditor({
  kind,
  record,
  fields,
  backHref,
  backLabel,
  onSaved,
  workspaceId = CRM_WORKSPACE,
}: CrmDetailEditorProps) {
  const [draft, setDraft] = React.useState<Record<string, string>>({});
  const [stage, setStage] = React.useState(String(record.stage || ""));
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [note, setNote] = React.useState("");

  const entityType = singularKind(kind);
  const activities = useSWR(["crm-activities", workspaceId, entityType, record.id], () =>
    fetchCrmActivities(workspaceId, { entity_type: entityType, entity_id: record.id }),
  );

  React.useEffect(() => {
    const next: Record<string, string> = {};
    for (const field of fields) {
      if (field.key === "email") {
        next.email = primaryEmail(record);
      } else if (field.key === "tags") {
        next.tags = Array.isArray(record.tags) ? record.tags.join(", ") : String(record.tags ?? "");
      } else {
        const raw = record[field.key];
        next[field.key] = raw === null || raw === undefined ? "" : String(raw);
      }
    }
    setDraft(next);
    setStage(String(record.stage || ""));
  }, [record, fields]);

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const body: Record<string, unknown> = {
        expected_version: record.version,
      };
      for (const field of fields) {
        const value = draft[field.key]?.trim() ?? "";
        if (field.key === "email") {
          body.emails = value ? [{ address: value, primary: true }] : [];
        } else if (field.key === "tags") {
          body.tags = value
            ? value
                .split(",")
                .map((t) => t.trim())
                .filter(Boolean)
            : [];
        } else {
          body[field.key] = value || null;
        }
      }
      if (stage) body.stage = stage;
      const result = await patchCrmRecord(kind, record.id, body, workspaceId);
      if (result.blocked) {
        setMessage("Soft Wall blocked this change; approval queued.");
      } else {
        const updated = (result[entityType] || result.list || result) as CrmRecord;
        setMessage("Saved");
        onSaved?.(updated);
      }
      await activities.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    } finally {
      setBusy(false);
    }
  };

  const addNote = async () => {
    if (!note.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createCrmActivity(
        {
          entity_type: entityType,
          entity_id: record.id,
          activity_type: "note",
          channel: "workspace",
          subject: "Operator note",
          body: note.trim(),
        },
        workspaceId,
      );
      setNote("");
      setMessage("Activity added");
      await activities.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add activity");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2} sx={{ maxWidth: 800 }}>
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

      <Button size="small" component={Link} href={backHref} sx={{ alignSelf: "flex-start" }}>
        {backLabel}
      </Button>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="h5">{displayName(record)}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {stageLabel(record.stage)}
            {primaryEmail(record) ? ` · ${primaryEmail(record)}` : ""}
            {record.last_touch_at ? ` · last touch ${formatTouch(record.last_touch_at)}` : ""}
          </Typography>
          <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mt: 1.5 }}>
            {provenanceBadges(record).map((badge) => (
              <Chip key={badge.label} size="small" label={badge.label} title={badge.hint} variant="outlined" />
            ))}
          </Stack>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Edit fields
          </Typography>
          <Stack spacing={1.5}>
            {fields.map((field) => (
              <TextField
                key={field.key}
                size="small"
                fullWidth
                label={field.label}
                multiline={Boolean(field.multiline)}
                minRows={field.multiline ? 3 : undefined}
                value={draft[field.key] ?? ""}
                onChange={(e) => setDraft((prev) => ({ ...prev, [field.key]: e.target.value }))}
              />
            ))}
            <FormControl size="small" fullWidth>
              <InputLabel id={`${kind}-stage`}>Stage</InputLabel>
              <Select
                labelId={`${kind}-stage`}
                label="Stage"
                value={stage}
                onChange={(e) => setStage(e.target.value)}
              >
                {CRM_STAGES.map((item) => (
                  <MenuItem key={item} value={item}>
                    {stageLabel(item)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Button size="small" variant="contained" disabled={busy} onClick={() => void save()}>
                Save
              </Button>
              {(kind === "leads" || kind === "contacts") && (
                <Button
                  size="small"
                  variant="outlined"
                  disabled={busy}
                  onClick={() => {
                    void (async () => {
                      setBusy(true);
                      setError(null);
                      try {
                        const result = await offerCrmBooking(kind, record.id, {}, workspaceId);
                        const gui = (result.gui || {}) as Record<string, string>;
                        setMessage(
                          result.ok
                            ? `Booking offer: ${gui.open_booking || "see GUI links"}`
                            : String(result.message || result.reason || "Booking unavailable"),
                        );
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Offer booking failed");
                      } finally {
                        setBusy(false);
                      }
                    })();
                  }}
                >
                  Offer booking
                </Button>
              )}
              {(kind === "leads" || kind === "contacts") && (
                <Button
                  size="small"
                  variant="outlined"
                  disabled={busy}
                  onClick={() => {
                    void (async () => {
                      setBusy(true);
                      setError(null);
                      try {
                        await createCrmConsent(
                          {
                            subject_type: entityType,
                            subject_id: record.id,
                            channel: "email",
                            lawful_basis: "legitimate_interest",
                            purpose: "outreach",
                            evidence: "operator_ui",
                            source: "crm_detail",
                          },
                          workspaceId,
                        );
                        setMessage("Consent recorded (legitimate_interest)");
                        await activities.mutate();
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Consent failed");
                      } finally {
                        setBusy(false);
                      }
                    })();
                  }}
                >
                  Record consent
                </Button>
              )}
              {(kind === "leads" || kind === "contacts") && (
                <Button
                  size="small"
                  variant="outlined"
                  disabled={busy}
                  onClick={() => {
                    void (async () => {
                      setBusy(true);
                      setError(null);
                      try {
                        const result = await exportCrmSubject(kind, record.id, {}, workspaceId);
                        if (result.blocked) {
                          setMessage(`Soft Wall export pending: ${(result.approval as { id?: string } | undefined)?.id || ""}`);
                        } else {
                          setMessage("Subject access export ready (see API response / Soft Wall)");
                        }
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Export failed");
                      } finally {
                        setBusy(false);
                      }
                    })();
                  }}
                >
                  DSAR export
                </Button>
              )}
              <Button size="small" variant="outlined" component={Link} href="/outreach/approvals">
                Soft Wall inbox
              </Button>
              <Button size="small" variant="outlined" component={Link} href="/outreach">
                Soft Wall outreach
              </Button>
              <Button size="small" variant="outlined" component={Link} href="/vical">
                viCal
              </Button>
              <Button size="small" variant="outlined" component={Link} href="/calendar">
                Calendar
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Activity timeline
          </Typography>
          {activities.isLoading && !activities.data ? (
            <Typography color="text.secondary">Loading activities...</Typography>
          ) : (activities.data?.items ?? []).length === 0 ? (
            <Typography color="text.secondary" sx={{ mb: 1.5 }}>
              No activities yet for this record.
            </Typography>
          ) : (
            <Stack spacing={1} sx={{ mb: 1.5 }}>
              {(activities.data?.items ?? []).map((item) => (
                <Typography key={item.id} variant="body2" color="text.secondary">
                  {item.created_at ? `${formatTouch(item.created_at)} · ` : ""}
                  {item.activity_type || "activity"}
                  {item.subject ? ` · ${item.subject}` : ""}
                  {item.body ? ` · ${item.body}` : ""}
                </Typography>
              ))}
            </Stack>
          )}
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <TextField
              size="small"
              fullWidth
              label="Add note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
            <Button size="small" variant="outlined" disabled={busy} onClick={() => void addNote()}>
              Add
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}

export default CrmDetailEditor;
