"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { cancelCrmOutbox, fetchCrmOutbox, retryCrmOutbox } from "@/lib/crm-api";

export default function CrmOutboxPage() {
  const [error, setError] = React.useState<string | null>(null);
  const [filter, setFilter] = React.useState<string | undefined>(undefined);
  const outbox = useSWR(["crm-outbox", CRM_WORKSPACE, filter], () => fetchCrmOutbox(CRM_WORKSPACE, filter));

  const act = async (id: string, action: "retry" | "cancel") => {
    setError(null);
    try {
      if (action === "retry") await retryCrmOutbox(id, {}, CRM_WORKSPACE);
      else await cancelCrmOutbox(id, CRM_WORKSPACE);
      await outbox.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    }
  };

  const items = outbox.data?.items || [];
  const dead = items.filter((i) => String(i.status) === "dead_letter");

  return (
    <Stack spacing={2}>
      <Typography variant="body2" color="text.secondary">
        Transactional outbox with idempotency keys. Failed and dead-letter sends show here.
      </Typography>
      {error ? <Alert severity="error">{error}</Alert> : null}
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        {["", "pending", "sent", "failed", "dead_letter"].map((s) => (
          <Button
            key={s || "all"}
            size="small"
            variant={filter === (s || undefined) ? "contained" : "outlined"}
            onClick={() => setFilter(s || undefined)}
          >
            {s || "all"}
          </Button>
        ))}
      </Stack>
      <Typography variant="caption" color="text.secondary">
        Dead letters: {dead.length}
      </Typography>
      {outbox.isLoading ? (
        <Typography color="text.secondary">Loading outbox...</Typography>
      ) : items.length === 0 ? (
        <Typography color="text.secondary">No outbox rows.</Typography>
      ) : (
        <Stack spacing={1}>
          {items.map((row) => (
            <Card key={String(row.id)} variant="outlined">
              <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                <Typography variant="body2" fontWeight={600}>
                  {String(row.kind)} · {String(row.status)}
                </Typography>
                <Typography variant="caption" color="text.secondary" display="block">
                  idempotency {String(row.idempotency_key || "")}
                </Typography>
                {row.last_error ? (
                  <Typography variant="caption" color="error.main" display="block">
                    {String(row.last_error)}
                  </Typography>
                ) : null}
                <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                  {["failed", "dead_letter"].includes(String(row.status)) ? (
                    <Button size="small" onClick={() => void act(String(row.id), "retry")}>
                      Retry
                    </Button>
                  ) : null}
                  {String(row.status) === "pending" ? (
                    <Button size="small" onClick={() => void act(String(row.id), "cancel")}>
                      Cancel
                    </Button>
                  ) : null}
                </Stack>
              </CardContent>
            </Card>
          ))}
        </Stack>
      )}
    </Stack>
  );
}
