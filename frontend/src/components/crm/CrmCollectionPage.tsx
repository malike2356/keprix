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
import CrmEntityTable from "@/components/crm/CrmEntityTable";
import {
  CRM_WORKSPACE,
  type CrmEntityKind,
  type CrmRecord,
} from "@/components/crm/types";
import {
  bulkDeleteCrmLeads,
  createCrmRecord,
  deleteCrmRecord,
  fetchCrmCollection,
  patchCrmRecord,
} from "@/lib/crm-api";

type CreateField = {
  key: string;
  label: string;
  required?: boolean;
};

type CrmCollectionPageProps = {
  kind: CrmEntityKind;
  title: string;
  description: string;
  createFields: CreateField[];
  buildCreateBody: (draft: Record<string, string>) => Record<string, unknown>;
  emptyMessage: string;
  showCompanyAsName?: boolean;
};

export function CrmCollectionPage({
  kind,
  title,
  description,
  createFields,
  buildCreateBody,
  emptyMessage,
  showCompanyAsName = false,
}: CrmCollectionPageProps) {
  const [draft, setDraft] = React.useState<Record<string, string>>({});
  const [query, setQuery] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());

  const list = useSWR(["crm-collection", kind, CRM_WORKSPACE, query], () =>
    fetchCrmCollection(kind, CRM_WORKSPACE, { q: query || undefined, limit: 200 }),
  );

  const rows = list.data?.items ?? [];

  const onCreate = async () => {
    setBusy(true);
    setError(null);
    try {
      for (const field of createFields) {
        if (field.required && !draft[field.key]?.trim()) {
          throw new Error(`${field.label} is required`);
        }
      }
      await createCrmRecord(kind, buildCreateBody(draft), CRM_WORKSPACE);
      setDraft({});
      setMessage(`${title.slice(0, -1) || "Record"} created`);
      await list.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create");
    } finally {
      setBusy(false);
    }
  };

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    setSelected((prev) => {
      if (prev.size === rows.length) return new Set();
      return new Set(rows.map((row) => row.id));
    });
  };

  const bulkSuppress = async () => {
    if (selected.size === 0) return;
    setBusy(true);
    setError(null);
    try {
      for (const id of selected) {
        await patchCrmRecord(kind, id, { stage: "suppressed" }, CRM_WORKSPACE);
      }
      setMessage(`Suppressed ${selected.size} record(s)`);
      setSelected(new Set());
      await list.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk suppress failed");
    } finally {
      setBusy(false);
    }
  };

  const bulkDelete = async () => {
    if (selected.size === 0) return;
    setBusy(true);
    setError(null);
    try {
      const ids = Array.from(selected);
      if (kind === "leads") {
        await bulkDeleteCrmLeads(ids, { preview: false, reason: "operator bulk delete" }, CRM_WORKSPACE);
      } else {
        for (const id of ids) {
          await deleteCrmRecord(kind, id, CRM_WORKSPACE);
        }
      }
      setMessage(`Deleted ${ids.length} record(s)`);
      setSelected(new Set());
      await list.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk delete failed");
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
        {description}
      </Typography>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Add {title.toLowerCase().replace(/s$/, "")}
          </Typography>
          <Stack spacing={1.5}>
            {createFields.map((field) => (
              <TextField
                key={field.key}
                size="small"
                label={field.label}
                value={draft[field.key] ?? ""}
                onChange={(e) => setDraft((prev) => ({ ...prev, [field.key]: e.target.value }))}
              />
            ))}
            <Button size="small" variant="contained" disabled={busy} onClick={() => void onCreate()}>
              Save
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }}>
        <TextField
          size="small"
          label="Search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          sx={{ minWidth: 220 }}
        />
        <Button size="small" variant="outlined" disabled={busy || selected.size === 0} onClick={() => void bulkSuppress()}>
          Suppress selected
        </Button>
        <Button size="small" variant="outlined" color="error" disabled={busy || selected.size === 0} onClick={() => void bulkDelete()}>
          Delete selected
        </Button>
        <Button size="small" variant="outlined" component="a" href="/outreach" disabled={selected.size === 0}>
          Enroll via Soft Wall
        </Button>
      </Stack>

      {list.isLoading && !list.data ? (
        <Typography color="text.secondary">Loading {title.toLowerCase()}...</Typography>
      ) : (
        <CrmEntityTable
          rows={rows as CrmRecord[]}
          hrefFor={(row) => `/crm/${kind}/${row.id}`}
          selectedIds={selected}
          onToggle={toggle}
          onToggleAll={toggleAll}
          emptyMessage={emptyMessage}
          showCompanyAsName={showCompanyAsName}
        />
      )}
    </Stack>
  );
}

export default CrmCollectionPage;
