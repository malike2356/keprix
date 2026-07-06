"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";

export type CheckoutLine = {
  label: string;
  amount: string;
};

type CheckoutSummaryProps = {
  lines: CheckoutLine[];
  total: string;
  loading?: boolean;
  onConfirm?: () => void;
  confirmLabel?: string;
};

export default function CheckoutSummary({
  lines,
  total,
  loading = false,
  onConfirm,
  confirmLabel = "Confirm checkout",
}: CheckoutSummaryProps) {
  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 2 }}>
      <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1.5 }}>Order summary</Typography>
      <Box sx={{ display: "grid", gap: 1 }}>
        {lines.map((line) => (
          <Box key={line.label} sx={{ display: "flex", justifyContent: "space-between" }}>
            <Typography variant="body2">{line.label}</Typography>
            <Typography variant="body2">{line.amount}</Typography>
          </Box>
        ))}
      </Box>
      <Divider sx={{ my: 1.5 }} />
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="subtitle2">Total</Typography>
        <Typography variant="subtitle2">{total}</Typography>
      </Box>
      {onConfirm ? (
        <Button fullWidth variant="contained" disabled={loading} onClick={onConfirm}>
          {confirmLabel}
        </Button>
      ) : null}
    </Box>
  );
}
