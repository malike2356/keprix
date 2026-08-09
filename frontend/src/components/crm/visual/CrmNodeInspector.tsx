"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { createCrmSupportBundle, fetchCrmNodeInspector } from "@/lib/crm-api";

type Props = {
  workflowId: string;
  nodeId: string | null;
  mode?: "design" | "simulation" | "live" | "replay";
  runId?: string | null;
  onClose?: () => void;
};

export default function CrmNodeInspector({ workflowId, nodeId, mode = "design", runId, onClose }: Props) {
  const [tab, setTab] = React.useState(0);
  const [bundleMsg, setBundleMsg] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const insp = useSWR(
    nodeId ? ["crm-inspector", CRM_WORKSPACE, workflowId, nodeId, mode, runId] : null,
    () =>
      fetchCrmNodeInspector(
        {
          workflow_id: workflowId,
          node_id: nodeId!,
          mode,
          run_id: runId || undefined,
        },
        CRM_WORKSPACE,
      ),
  );

  if (!nodeId) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Select a node to inspect purpose, policy, evidence, and attempts.
        </Typography>
      </Box>
    );
  }

  const tabs = (insp.data?.tabs_order as string[]) || [];
  const tabData = (insp.data?.tabs as Record<string, unknown>) || {};
  const activeKey = tabs[tab] || "overview";
  const active = tabData[activeKey];

  const makeBundle = async () => {
    setError(null);
    try {
      const res = await createCrmSupportBundle(
        { workflow_id: workflowId, run_id: runId, node_ids: [nodeId] },
        CRM_WORKSPACE,
      );
      setBundleMsg(`Support bundle ${String(res.bundle_id)} (redacted)`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bundle failed");
    }
  };

  return (
    <Box sx={{ p: 2, height: "100%", overflow: "auto" }} aria-label="Node inspector">
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="subtitle1">Node inspector</Typography>
        {onClose ? (
          <Button size="small" onClick={onClose}>
            Close
          </Button>
        ) : null}
      </Stack>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
        Mode: {mode} · Node: {nodeId}
      </Typography>
      {error ? <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert> : null}
      {bundleMsg ? <Alert severity="success" sx={{ mb: 1 }}>{bundleMsg}</Alert> : null}
      {insp.isLoading ? (
        <Typography color="text.secondary">Loading inspector...</Typography>
      ) : insp.error ? (
        <Alert severity="error">Could not load inspector</Alert>
      ) : (
        <>
          <Tabs
            value={tab}
            onChange={(_, v) => setTab(v)}
            variant="scrollable"
            allowScrollButtonsMobile
            sx={{ minHeight: 36, mb: 1 }}
          >
            {tabs.map((t) => (
              <Tab key={t} label={t.replace(/_/g, " ")} sx={{ minHeight: 36, textTransform: "none" }} />
            ))}
          </Tabs>
          <Box
            sx={{
              p: 1.5,
              bgcolor: "action.hover",
              borderRadius: 1,
            }}
          >
            <StructuredDataView value={active} />
          </Box>
          <Divider sx={{ my: 1.5 }} />
          <Stack spacing={0.5}>
            {Object.entries((insp.data?.links as Record<string, string | null>) || {}).map(([k, href]) =>
              href ? (
                <Typography key={k} component="a" href={href} variant="caption" color="primary">
                  {k}: {href}
                </Typography>
              ) : null,
            )}
          </Stack>
          <Button size="small" sx={{ mt: 1.5 }} onClick={() => void makeBundle()}>
            Create redacted support bundle
          </Button>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            Secrets and unrestricted prompts stay redacted. Model inference is never labelled verified.
          </Typography>
        </>
      )}
    </Box>
  );
}
