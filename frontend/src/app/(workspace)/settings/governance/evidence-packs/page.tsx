"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import {
  generateEvidencePack,
  listEvidencePacks,
  sendEvidencePackToProvider,
  type EvidencePackRecord,
} from "@/lib/evidence-pack-api";

export default function EvidencePacksPage() {
  const { data: packs, mutate } = useSWR("evidence-packs", listEvidencePacks);
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const onGenerate = async () => {
    setBusy(true);
    setError(null);
    try {
      await generateEvidencePack({
        date_from: new Date(dateFrom).toISOString(),
        date_to: new Date(dateTo).toISOString(),
        include_documents: true,
      });
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  };

  const onSendToProvider = async (packId: string) => {
    setError(null);
    try {
      await sendEvidencePackToProvider(packId);
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Governance provider upload failed");
    }
  };

  return (
    <Box>
      <PageHeader
        title="Evidence packs"
        description="Generate signed audit event archives for auditors and governance provider ingestion."
      />
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb: 3 }}>
        <TextField
          label="Date from"
          type="datetime-local"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Date to"
          type="datetime-local"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <Button variant="contained" onClick={onGenerate} disabled={busy || !dateFrom || !dateTo}>
          Generate pack
        </Button>
      </Stack>
      <Stack spacing={1}>
        {(packs ?? []).map((pack: EvidencePackRecord) => (
          <Box key={pack.pack_id} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 1, p: 2 }}>
            <Typography variant="subtitle2">{pack.pack_id}</Typography>
            <Typography variant="body2" color="text.secondary">
              {pack.status} | {pack.event_count} events | {pack.document_count} documents
            </Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
              {pack.download_url ? (
                <Button size="small" href={pack.download_url} target="_blank" rel="noreferrer">
                  Download
                </Button>
              ) : null}
              <Button size="small" onClick={() => onSendToProvider(pack.pack_id)}>
                Send to provider
              </Button>
            </Stack>
          </Box>
        ))}
      </Stack>
    </Box>
  );
}
