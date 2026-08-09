"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { CRM_WORKSPACE } from "@/components/crm/types";
import {
  claimCrmInboxItem,
  fetchCrmInbox,
  pauseCrmInboxItem,
  resumeCrmInboxItem,
} from "@/lib/crm-api";

const TABS = [
  { key: "reply", label: "Replies" },
  { key: "stage_suggestion", label: "Stage suggestions" },
  { key: "takeover", label: "Takeover" },
  { key: "complaint", label: "Complaints" },
] as const;

export default function CrmInboxPage() {
  const [tab, setTab] = React.useState(0);
  const [error, setError] = React.useState<string | null>(null);
  const kind = TABS[tab]?.key;
  const inbox = useSWR(["crm-inbox", CRM_WORKSPACE, kind], () =>
    fetchCrmInbox(CRM_WORKSPACE, { status: "open", kind }),
  );

  const act = async (id: string, action: "claim" | "pause" | "resume") => {
    setError(null);
    try {
      if (action === "claim") await claimCrmInboxItem(id, CRM_WORKSPACE);
      if (action === "pause") await pauseCrmInboxItem(id, CRM_WORKSPACE);
      if (action === "resume") await resumeCrmInboxItem(id, CRM_WORKSPACE);
      await inbox.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    }
  };

  return (
    <Stack spacing={2}>
      <Typography variant="body2" color="text.secondary">
        Engagement replies, Soft Wall stage suggestions, takeover, and complaints. Claim from here without Telegram.
      </Typography>
      {error ? <Alert severity="error">{error}</Alert> : null}
      <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="scrollable">
        {TABS.map((t) => (
          <Tab key={t.key} label={t.label} />
        ))}
      </Tabs>
      {inbox.isLoading ? (
        <Typography color="text.secondary">Loading inbox...</Typography>
      ) : (inbox.data?.items || []).length === 0 ? (
        <Typography color="text.secondary">No open {TABS[tab]?.label.toLowerCase()} items.</Typography>
      ) : (
        <Stack spacing={1}>
          {(inbox.data?.items || []).map((item) => (
            <Card key={String(item.id)} variant="outlined">
              <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                <Typography variant="body2" fontWeight={600}>
                  {String(item.classification || item.kind || "item")} · {String(item.subject || "")}
                </Typography>
                <Typography variant="caption" color="text.secondary" display="block">
                  {String(item.entity_type || "")} {String(item.entity_id || "")} · confidence{" "}
                  {String(item.confidence ?? "")}
                </Typography>
                <Typography variant="body2" sx={{ mt: 0.5 }} noWrap>
                  {String(item.body || "").slice(0, 160)}
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 1 }} flexWrap="wrap" useFlexGap>
                  <Button size="small" onClick={() => void act(String(item.id), "claim")}>
                    Claim
                  </Button>
                  <Button size="small" onClick={() => void act(String(item.id), "pause")}>
                    Pause
                  </Button>
                  <Button size="small" onClick={() => void act(String(item.id), "resume")}>
                    Resume
                  </Button>
                  {item.entity_id ? (
                    <Button
                      size="small"
                      component="a"
                      href={`/crm/${item.entity_type === "contact" ? "contacts" : "leads"}/${item.entity_id}`}
                    >
                      Open CRM
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
