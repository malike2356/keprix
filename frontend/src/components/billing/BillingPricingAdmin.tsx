"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { SkeletonTable } from "@/components/ui/loading";
import {
  fetchBillingAdminCatalog,
  fetchBillingAdminPricing,
  saveBillingAdminPricing,
  type BillingAdminPlan,
  type BillingPlanModelPolicy,
} from "@/lib/billing-api";

type PriceSelection = Record<string, Record<"month" | "year", string>>;
type ModelPolicySelection = Record<string, BillingPlanModelPolicy>;

function buildSelection(plans: BillingAdminPlan[]): PriceSelection {
  const selection: PriceSelection = {};
  for (const plan of plans) {
    selection[plan.id] = { month: "", year: "" };
    for (const price of plan.prices) {
      if (price.interval === "month" || price.interval === "year") {
        selection[plan.id][price.interval] = "";
      }
    }
  }
  return selection;
}

export default function BillingPricingAdmin() {
  const { data: pricing, isLoading: pricingLoading, mutate } = useSWR(
    "billing-admin-pricing",
    fetchBillingAdminPricing,
  );
  const { data: catalog, isLoading: catalogLoading } = useSWR(
    "billing-admin-catalog",
    fetchBillingAdminCatalog,
  );

  const [selection, setSelection] = React.useState<PriceSelection>({});
  const [modelPolicies, setModelPolicies] = React.useState<ModelPolicySelection>({});
  const [saving, setSaving] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (pricing?.plans) {
      setSelection(buildSelection(pricing.plans));
      setModelPolicies(
        Object.fromEntries(
          pricing.plans.map((plan) => [
            plan.id,
            {
              allowed_providers: [...(plan.plan_model_policy?.allowed_providers || [])],
              allowed_models: [...(plan.plan_model_policy?.allowed_models || [])],
              default_model: plan.plan_model_policy?.default_model || null,
            },
          ]),
        ),
      );
    }
  }, [pricing]);

  const catalogItems = catalog?.items || [];

  const onSelect = (planId: string, interval: "month" | "year", priceId: string) => {
    setSelection((current) => ({
      ...current,
      [planId]: { ...current[planId], [interval]: priceId },
    }));
  };

  const onPolicyChange = (
    planId: string,
    field: "allowed_providers" | "allowed_models" | "default_model",
    value: string,
  ) => {
    setModelPolicies((current) => ({
      ...current,
      [planId]: {
        ...current[planId],
        [field]: field === "default_model"
          ? value || null
          : value.split(",").map((item) => item.trim()).filter(Boolean),
      },
    }));
  };

  const onSave = async () => {
    if (!pricing) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const body = {
        plans: pricing.plans.map((plan) => ({
          id: plan.id,
          prices: (["month", "year"] as const)
            .filter((interval) => selection[plan.id]?.[interval])
            .map((interval) => ({
              interval,
              stripe_price_id: selection[plan.id][interval],
            })),
          plan_model_policy: modelPolicies[plan.id] || {
            allowed_providers: [],
            allowed_models: [],
            default_model: null,
          },
        })),
      };
      await saveBillingAdminPricing(body);
      setMessage("Pricing saved");
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save pricing");
    } finally {
      setSaving(false);
    }
  };

  if (pricingLoading || catalogLoading) {
    return <SkeletonTable rows={4} columns={3} />;
  }

  if (!pricing) {
    return <Alert severity="error">Could not load plan pricing.</Alert>;
  }

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Map each plan to a Stripe price. Prices are read from the Stripe catalog configured for this
        product; use {pricing.config_path} as the source of truth for IDs.
      </Typography>

      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}

      <Paper variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Plan</TableCell>
              <TableCell>Monthly price</TableCell>
              <TableCell>Yearly price</TableCell>
              <TableCell>Model policy</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {pricing.plans.map((plan) => (
              <TableRow key={plan.id}>
                <TableCell>
                  <Typography variant="body2" fontWeight={600}>
                    {plan.name}
                  </Typography>
                  {plan.description ? (
                    <Typography variant="caption" color="text.secondary">
                      {plan.description}
                    </Typography>
                  ) : null}
                </TableCell>
                {(["month", "year"] as const).map((interval) => (
                  <TableCell key={interval}>
                    <TextField
                      select
                      size="small"
                      fullWidth
                      value={selection[plan.id]?.[interval] || ""}
                      onChange={(event) => onSelect(plan.id, interval, event.target.value)}
                    >
                      <MenuItem value="">Not set</MenuItem>
                      {catalogItems.map((item) => (
                        <MenuItem key={item.price_id} value={item.price_id}>
                          {item.label} ({item.price_id})
                        </MenuItem>
                      ))}
                    </TextField>
                  </TableCell>
                ))}
                <TableCell sx={{ minWidth: 360 }}>
                  <Stack spacing={1}>
                    <TextField
                      size="small"
                      label="Allowed providers"
                      value={(modelPolicies[plan.id]?.allowed_providers || []).join(", ")}
                      onChange={(event) => onPolicyChange(plan.id, "allowed_providers", event.target.value)}
                      placeholder="openai, anthropic"
                      helperText="Comma-separated; empty means any provider"
                    />
                    <TextField
                      size="small"
                      label="Allowed models"
                      value={(modelPolicies[plan.id]?.allowed_models || []).join(", ")}
                      onChange={(event) => onPolicyChange(plan.id, "allowed_models", event.target.value)}
                      placeholder="gpt-4.1-mini, claude-sonnet-4-6"
                      helperText="Model IDs or provider:model IDs"
                    />
                    <TextField
                      size="small"
                      label="Default model"
                      value={modelPolicies[plan.id]?.default_model || ""}
                      onChange={(event) => onPolicyChange(plan.id, "default_model", event.target.value)}
                      placeholder="provider:model"
                    />
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      <Stack direction="row" justifyContent="flex-end" sx={{ mt: 2 }}>
        <Button variant="contained" disabled={saving} onClick={() => void onSave()}>
          {saving ? "Saving..." : "Save pricing"}
        </Button>
      </Stack>
    </Box>
  );
}
