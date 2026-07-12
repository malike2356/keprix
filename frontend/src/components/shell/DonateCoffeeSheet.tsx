"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { createDonationCheckout } from "@/lib/billing-api";

const PRESETS = [1, 3, 5, 10] as const;
const MIN_GBP = 1;
const MAX_GBP = 500;

type DonateCoffeeSheetProps = {
  open: boolean;
  onClose: () => void;
};

export default function DonateCoffeeSheet({ open, onClose }: DonateCoffeeSheetProps) {
  const [amount, setAmount] = React.useState<string>("1");
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setAmount("1");
      setError(null);
      setLoading(false);
    }
  }, [open]);

  const parsed = Number(amount);
  const valid =
    Number.isFinite(parsed) && parsed >= MIN_GBP && parsed <= MAX_GBP && /^\d+(\.\d{1,2})?$/.test(amount.trim());

  async function handleContinue() {
    if (!valid) {
      setError(`Enter an amount between £${MIN_GBP} and £${MAX_GBP}`);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await createDonationCheckout(parsed);
      if (!result.checkout_url) {
        throw new Error("Checkout URL missing");
      }
      window.location.href = result.checkout_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start donation checkout");
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onClose={loading ? undefined : onClose} fullWidth maxWidth="xs">
      <DialogTitle>Buy us a coffee</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
        <Typography variant="body2" color="text.secondary">
          Optional support for Keprix Community Edition. From £{MIN_GBP}. Never required.
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          {PRESETS.map((preset) => (
            <Button
              key={preset}
              size="small"
              variant={Number(amount) === preset ? "contained" : "outlined"}
              onClick={() => {
                setAmount(String(preset));
                setError(null);
              }}
              disabled={loading}
            >
              £{preset}
            </Button>
          ))}
        </Box>
        <TextField
          label="Custom amount (GBP)"
          type="number"
          value={amount}
          onChange={(event) => {
            setAmount(event.target.value);
            setError(null);
          }}
          inputProps={{ min: MIN_GBP, max: MAX_GBP, step: "0.01" }}
          helperText={`Minimum £${MIN_GBP}. Maximum £${MAX_GBP}.`}
          disabled={loading}
          fullWidth
        />
        {error ? (
          <Typography variant="body2" color="error">
            {error}
          </Typography>
        ) : null}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button variant="contained" onClick={handleContinue} disabled={loading || !valid}>
          {loading ? "Opening Stripe..." : `Donate £${valid ? parsed.toFixed(2) : "-"}`}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
