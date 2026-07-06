"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { useCESession } from "@/lib/ce-auth";
import {
  approvePackGateRecord,
  fetchPackGateConfig,
  fetchPackGateRecord,
  rejectPackGateRecord,
} from "@/lib/pack-gate-api";

type PageProps = {
  params: Promise<{ pack_id: string }>;
};

export default function PackGateSignOffPage({ params }: PageProps) {
  const { pack_id: packId } = React.use(params);
  const searchParams = useSearchParams();
  const recordId = searchParams.get("record");
  const { user } = useCESession();
  const { data: config } = useSWR("pack-gate-config", fetchPackGateConfig);
  const { data: record, mutate } = useSWR(
    recordId ? `pack-gate-record-${recordId}` : null,
    () => fetchPackGateRecord(recordId as string),
  );
  const [note, setNote] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const isApprover =
    user?.role === "admin" ||
    user?.role === "owner" ||
    (config?.approver_user_id && user?.id === config.approver_user_id);
  const readOnly = !record || record.status !== "pending" || !isApprover;

  const declaration =
    record &&
    `By clicking Approve and activate, I confirm that I have reviewed the changes described above and accept responsibility for activating version ${record.to_version} of ${record.pack_id} in this workspace.`;

  const handleApprove = async () => {
    if (!recordId) return;
    setBusy(true);
    setError(null);
    try {
      await approvePackGateRecord(recordId, note || undefined);
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  };

  const handleReject = async () => {
    if (!recordId) return;
    if (!note.trim()) {
      setError("A rejection note is required.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await rejectPackGateRecord(recordId, note.trim());
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reject failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title={`Pack sign-off: ${packId}`}
        description="Review changelog and approve or reject activation."
      />
      {!recordId ? <Alert severity="info">No gate record selected.</Alert> : null}
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      {!isApprover && record?.status === "pending" ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Only the configured approver can sign off on pack changes.
        </Alert>
      ) : null}
      {record ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" sx={{ mb: 1 }}>
              {record.pack_id} v{record.to_version}
            </Typography>
            <Typography color="text.secondary" sx={{ mb: 2 }}>
              Status: {record.status}
              {record.from_version ? ` | from v${record.from_version}` : ""}
            </Typography>
            <Typography sx={{ mb: 2, whiteSpace: "pre-wrap" }}>
              {record.changelog_text || "No changelog text was provided."}
            </Typography>
            {record.status === "pending" ? (
              <>
                <Typography sx={{ mb: 2 }}>{declaration}</Typography>
                <TextField
                  fullWidth
                  multiline
                  minRows={3}
                  label="Note"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  disabled={readOnly || busy}
                  sx={{ mb: 2 }}
                />
                <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                  <Button variant="contained" disabled={readOnly || busy} onClick={() => void handleApprove()}>
                    Approve and activate
                  </Button>
                  <Button variant="outlined" color="error" disabled={readOnly || busy} onClick={() => void handleReject()}>
                    Reject
                  </Button>
                </Box>
              </>
            ) : (
              <Typography color="text.secondary">
                Signed off at {record.signed_off_at || "n/a"}
                {record.sign_off_note ? ` | ${record.sign_off_note}` : ""}
              </Typography>
            )}
          </CardContent>
        </Card>
      ) : null}
    </Box>
  );
}
