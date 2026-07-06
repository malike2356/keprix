"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import Link from "next/link";

export default function BillingDisabledState() {
  return (
    <Box
      sx={{
        border: 1,
        borderColor: "divider",
        borderRadius: 2,
        p: 4,
        textAlign: "center",
      }}
    >
      <Typography variant="h6" sx={{ mb: 1 }}>
        SaaS billing is not enabled on this instance
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 560, mx: "auto" }}>
        This Keprix deployment runs without subscription billing. Self-hosters can use the product without a paid plan.
        To enable billing for your product, set <code>KEPRIX_BILLING_ENABLED=true</code> and provide a billing config.
      </Typography>
      <Box sx={{ display: "flex", gap: 1, justifyContent: "center", flexWrap: "wrap" }}>
        <Button component={Link} href="/pricing" variant="outlined">
          View OSS pricing
        </Button>
        <Button
          component="a"
          href="https://github.com/keprix/keprix/blob/main/docs/features/billing.md"
          target="_blank"
          rel="noopener noreferrer"
          variant="text"
        >
          Billing setup docs
        </Button>
      </Box>
    </Box>
  );
}
