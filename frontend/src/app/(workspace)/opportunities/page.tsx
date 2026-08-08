"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import OpportunityCreatePanel from "@/components/opportunity/OpportunityCreatePanel";
import OpportunityStatusBadge from "@/components/opportunity/OpportunityStatusBadge";
import {
  listOpportunities,
  OPPORTUNITY_STATUSES,
  type OpportunityRecord,
} from "@/lib/opportunity-api";

export default function OpportunitiesPage() {
  const [rows, setRows] = React.useState<OpportunityRecord[]>([]);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    try {
      const payload = await listOpportunities();
      setRows(payload.opportunities);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load opportunities");
    }
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  return (
    <Box sx={{ p: { xs: 2, md: 3 }, maxWidth: 1200, mx: "auto" }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h5">Research opportunities</Typography>
          <Typography variant="body2" color="text.secondary">
            Product research opportunities (not sales CRM deals or Soft Wall pipeline).
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button component={NextLink} href="/crm/deals" size="small" variant="outlined">
            Sales deals
          </Button>
          <Button size="small" onClick={load}>
            Refresh
          </Button>
        </Stack>
      </Stack>
      <Alert severity="info" sx={{ mb: 2 }}>
        Looking for Soft Wall / CRM sales pipeline? Use{" "}
        <Button component={NextLink} href="/crm/deals" size="small">
          CRM deals
        </Button>{" "}
        or outreach sequences.
      </Alert>
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { md: "1fr 320px" } }}>
        <Box>
          <Stack spacing={1}>
            {rows.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No opportunities yet. Create one to start playbook execution.
              </Typography>
            ) : (
              rows.map((row) => (
                <Box
                  key={row.opportunity_id}
                  component={NextLink}
                  href={`/opportunities/${row.opportunity_id}`}
                  sx={{
                    display: "block",
                    p: 1.5,
                    border: 1,
                    borderColor: "divider",
                    borderRadius: 1,
                    textDecoration: "none",
                    color: "inherit",
                    "&:hover": { borderColor: "primary.main" },
                  }}
                >
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="subtitle2">{row.title}</Typography>
                    <OpportunityStatusBadge status={row.status} labels={OPPORTUNITY_STATUSES} />
                  </Stack>
                  <Typography variant="caption" color="text.secondary">
                    {row.opportunity_id}
                    {row.niche ? ` | ${row.niche}` : ""}
                  </Typography>
                </Box>
              ))
            )}
          </Stack>
        </Box>
        <OpportunityCreatePanel
          onCreated={(id) => {
            load();
            window.location.href = `/opportunities/${id}`;
          }}
        />
      </Box>
    </Box>
  );
}
