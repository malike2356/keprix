"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

type NodeCounts = Record<string, number>;

type ProductReadiness = {
  product?: string;
  engine_connectivity?: string;
  note?: string;
  pack_readiness?: {
    enabled?: boolean;
    pack_version?: string;
    contract_version?: string;
    crud_complete?: boolean;
    capability_honesty?: string;
    wrapper_of?: string | null;
  };
  node_counts?: NodeCounts;
  operation_counts?: NodeCounts;
  actor_and_tenant_binding?: {
    model?: string;
    model_cannot_override_identity?: boolean;
    grants?: string;
  };
  callback_health?: {
    connector_configured?: boolean;
    connector_base_url_env?: string;
    guidance?: string;
  };
  pending_approvals?: {
    count?: number;
    sample?: Array<Record<string, unknown>>;
  };
  event_lag?: {
    unacked_count?: number;
    lag_seconds?: number | null;
  };
  last_successful_canary?: {
    evidence_file_mtime?: string | null;
    last_read_receipt?: { node?: string; at?: string | null } | null;
    last_write_receipt?: { node?: string; at?: string | null } | null;
  };
  circuit?: Record<string, unknown>;
  emergency_controls?: {
    force_carina?: boolean;
    outbound_kill?: boolean;
    pack_enabled?: boolean;
    admin_route?: string;
  };
  source_of_truth?: string;
};

async function fetchReadiness(): Promise<ProductReadiness> {
  const response = await ceApi("/v1/products/propreneur/readiness");
  const body = (await response.json().catch(() => ({}))) as ProductReadiness & {
    detail?: string;
  };
  if (!response.ok) {
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : parseApiErrorMessage(body, `Readiness failed (${response.status})`),
    );
  }
  return body;
}

function countChip(label: string, value: number | undefined, color?: "default" | "success" | "warning" | "error") {
  return (
    <Chip
      size="small"
      color={color || "default"}
      label={`${label}: ${value ?? 0}`}
      sx={{ textTransform: "none" }}
    />
  );
}

export default function PropreneurPackReadinessPage() {
  const { data, error, mutate, isLoading } = useSWR("propreneur-product-readiness", fetchReadiness, {
    refreshInterval: 15_000,
  });
  const pack = data?.pack_readiness;
  const ops = data?.operation_counts || {};
  const pending = data?.pending_approvals?.count ?? 0;
  const honesty = pack?.capability_honesty || "unknown";

  return (
    <Box>
      <PageHeader
        title="Propreneur product pack"
        description="Pack readiness is not Universal Sidecar connectivity. Safe full CRUD means domain API access via Soft Wall, not raw database access."
      />

      <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        <Button component="a" href="/settings/sidecars" size="small" variant="outlined">
          Universal Sidecar
        </Button>
        <Button size="small" variant="outlined" onClick={() => mutate()}>
          Refresh
        </Button>
      </Stack>

      {error ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Could not load `/v1/products/propreneur/readiness`. {String(error.message || error)}
        </Alert>
      ) : null}

      {isLoading && !data ? (
        <Typography color="text.secondary">Loading pack readiness...</Typography>
      ) : null}

      {data ? (
        <Stack spacing={3}>
          <Alert severity={pack?.crud_complete ? "success" : "info"}>
            {data.note ||
              "HTTP health is engine connectivity only. CRUD readiness follows live and approval_required node counts."}
          </Alert>

          <Box>
            <Typography variant="h6" gutterBottom>
              Engine vs pack
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Chip
                size="small"
                color={data.engine_connectivity === "ok" ? "success" : "warning"}
                label={`engine: ${data.engine_connectivity || "unknown"}`}
              />
              <Chip
                size="small"
                color={pack?.enabled ? "success" : "error"}
                label={`pack: ${pack?.enabled ? "enabled" : "disabled"}`}
              />
              <Chip size="small" label={`honesty: ${honesty}`} />
              <Chip
                size="small"
                color={pack?.crud_complete ? "success" : "warning"}
                label={`crud_complete: ${pack?.crud_complete ? "yes" : "no"}`}
              />
              <Chip size="small" label={`pack ${pack?.pack_version || "?"}`} />
              <Chip size="small" label={`contract ${pack?.contract_version || "?"}`} />
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Source of truth: {data.source_of_truth || "Propreneur Laravel via /api/aiva/v1"}
            </Typography>
          </Box>

          <Box>
            <Typography variant="h6" gutterBottom>
              Operation counts
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {countChip("live", ops.live, "success")}
              {countChip("approval_required", ops.approval_required, "warning")}
              {countChip("proposal_only", ops.proposal_only)}
              {countChip("not_configured", ops.not_configured, ops.not_configured ? "warning" : "default")}
              {countChip("degraded", ops.degraded, ops.degraded ? "error" : "default")}
              {countChip(
                "intentionally_forbidden",
                ops.intentionally_forbidden,
                ops.intentionally_forbidden ? "error" : "default",
              )}
              {countChip("executable", ops.executable, "success")}
            </Stack>
          </Box>

          <Box>
            <Typography variant="h6" gutterBottom>
              Actor / tenant binding
            </Typography>
            <Typography variant="body2">
              Model: {data.actor_and_tenant_binding?.model || "TrustedExecutionContext"}. Model cannot
              override identity:{" "}
              {data.actor_and_tenant_binding?.model_cannot_override_identity === false ? "no" : "yes"}.
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {data.actor_and_tenant_binding?.grants ||
                "Delegated Aiva grant scopes + pack node required_grants"}
            </Typography>
          </Box>

          <Box>
            <Typography variant="h6" gutterBottom>
              Callbacks, approvals, events
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
              <Chip
                size="small"
                color={data.callback_health?.connector_configured ? "success" : "warning"}
                label={`connector: ${data.callback_health?.connector_configured ? "configured" : "missing"}`}
              />
              <Chip
                size="small"
                color={pending > 0 ? "warning" : "default"}
                label={`pending approvals: ${pending}`}
              />
              <Chip
                size="small"
                label={`unacked events: ${data.event_lag?.unacked_count ?? 0}`}
              />
              <Chip
                size="small"
                label={`event lag s: ${data.event_lag?.lag_seconds ?? "n/a"}`}
              />
            </Stack>
            <Typography variant="body2" color="text.secondary">
              Env: {data.callback_health?.connector_base_url_env || "PROPRENEUR_PRODUCT_API_URL"}.{" "}
              {data.callback_health?.guidance}
            </Typography>
          </Box>

          <Box>
            <Typography variant="h6" gutterBottom>
              Last canary / receipts
            </Typography>
            <Typography variant="body2">
              Evidence mtime: {data.last_successful_canary?.evidence_file_mtime || "n/a"}
            </Typography>
            <Typography variant="body2">
              Last read:{" "}
              {data.last_successful_canary?.last_read_receipt
                ? `${data.last_successful_canary.last_read_receipt.node} @ ${data.last_successful_canary.last_read_receipt.at}`
                : "none in local receipt store"}
            </Typography>
            <Typography variant="body2">
              Last write:{" "}
              {data.last_successful_canary?.last_write_receipt
                ? `${data.last_successful_canary.last_write_receipt.node} @ ${data.last_successful_canary.last_write_receipt.at}`
                : "none in local receipt store"}
            </Typography>
          </Box>

          <Box>
            <Typography variant="h6" gutterBottom>
              Circuit and emergency controls
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Chip size="small" label={`circuit: ${String(data.circuit?.state || data.circuit?.status || "unknown")}`} />
              <Chip
                size="small"
                color={data.emergency_controls?.force_carina ? "warning" : "default"}
                label={`force_carina: ${Boolean(data.emergency_controls?.force_carina)}`}
              />
              <Chip
                size="small"
                color={data.emergency_controls?.outbound_kill ? "error" : "default"}
                label={`outbound_kill: ${Boolean(data.emergency_controls?.outbound_kill)}`}
              />
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Admin kill route: {data.emergency_controls?.admin_route || "/v1/products/propreneur/admin/kill"}
            </Typography>
          </Box>
        </Stack>
      ) : null}
    </Box>
  );
}
