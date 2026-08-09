"use client";

import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { fetchCrmLeadActivities, fetchCrmLeadProvenance } from "@/lib/crm-api";
import { CRM_WORKSPACE } from "@/components/crm/types";

type CrmLeadProvenanceDrawerProps = {
  leadId: string | null;
  open: boolean;
  onClose: () => void;
  workspaceId?: string;
};

export default function CrmLeadProvenanceDrawer({
  leadId,
  open,
  onClose,
  workspaceId = CRM_WORKSPACE,
}: CrmLeadProvenanceDrawerProps) {
  const [tab, setTab] = React.useState(0);
  const provenance = useSWR(
    open && leadId ? ["crm-lead-prov", workspaceId, leadId] : null,
    () => fetchCrmLeadProvenance(leadId!, workspaceId),
  );
  const activities = useSWR(
    open && leadId ? ["crm-lead-acts", workspaceId, leadId] : null,
    () => fetchCrmLeadActivities(leadId!, workspaceId),
  );

  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: "100%", sm: 420 } } }}>
      <Stack spacing={1.5} sx={{ p: 2 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">Lead history</Typography>
          <IconButton aria-label="Close provenance drawer" onClick={onClose} size="small">
            X
          </IconButton>
        </Stack>
        <Typography variant="caption" color="text.secondary">
          {leadId || "No lead selected"}
        </Typography>
        <Tabs value={tab} onChange={(_, v) => setTab(v)} aria-label="Provenance and activity tabs">
          <Tab label="Provenance" />
          <Tab label="Activity" />
        </Tabs>
        {tab === 0 ? (
          <Stack spacing={1}>
            {(provenance.data?.items ?? []).length === 0 ? (
              <Typography color="text.secondary">No provenance rows.</Typography>
            ) : (
              (provenance.data?.items ?? []).map((row) => (
                <Stack key={String(row.id)} spacing={0.25} sx={{ borderBottom: 1, borderColor: "divider", pb: 1 }}>
                  <Typography variant="body2" fontWeight={600}>
                    {String(row.field_name || "field")}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {String(row.kind || "")} · {String(row.adapter || row.source_url || "")}
                  </Typography>
                </Stack>
              ))
            )}
          </Stack>
        ) : (
          <Stack spacing={1}>
            {(activities.data?.items ?? []).length === 0 ? (
              <Typography color="text.secondary">No activities.</Typography>
            ) : (
              (activities.data?.items ?? []).map((row) => (
                <Stack key={row.id} spacing={0.25} sx={{ borderBottom: 1, borderColor: "divider", pb: 1 }}>
                  <Typography variant="body2" fontWeight={600}>
                    {row.activity_type || "activity"}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {row.subject || row.body || row.created_at || ""}
                  </Typography>
                </Stack>
              ))
            )}
          </Stack>
        )}
      </Stack>
    </Drawer>
  );
}
