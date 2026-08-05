"use client";

import type { LegalPolicy } from "@/lib/legal-api";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import useSWR from "swr";
import { acceptPolicies, fetchLegalPolicies } from "@/lib/legal-api";

export default function LegalAcceptPage() {
  const { data } = useSWR("legal-policies", fetchLegalPolicies);
  const policies = data?.policies ?? [];
  const [checked, setChecked] = React.useState<Record<string, boolean>>({});
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const allChecked = policies.length > 0 && policies.every((policy) => checked[policy.policy_type]);

  const toggle = (policyType: string) => {
    setChecked((prev) => ({ ...prev, [policyType]: !prev[policyType] }));
  };

  const handleAccept = async () => {
    setBusy(true);
    setError(null);
    try {
      await acceptPolicies(policies.map((policy) => policy.policy_type));
      window.location.href = "/home";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Acceptance failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 3 }}>
      <Card sx={{ maxWidth: 720, width: "100%" }}>
        <CardContent>
          <Typography variant="h4" gutterBottom>
            Legal acceptance required
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 3 }}>
            You must accept the following policies to continue using this workspace.
          </Typography>
          {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
          {policies.map((policy: LegalPolicy) => (
            <Box key={policy.policy_type} sx={{ mb: 2 }}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={Boolean(checked[policy.policy_type])}
                    onChange={() => toggle(policy.policy_type)}
                  />
                }
                label={`${policy.title} (version ${policy.version})`}
              />
              <Typography variant="body2" color="text.secondary" sx={{ ml: 4 }}>
                {policy.summary}
              </Typography>
              <Link
                component={NextLink}
                href={policy.full_text_url}
                target="_blank"
                rel="noopener noreferrer"
                sx={{ ml: 4, display: "inline-block", mt: 0.5 }}
              >
                Read full policy
              </Link>
            </Box>
          ))}
          <Button variant="contained" disabled={!allChecked || busy} onClick={() => void handleAccept()}>
            Accept and continue
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
}
