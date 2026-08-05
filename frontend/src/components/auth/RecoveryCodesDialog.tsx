"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import Typography from "@mui/material/Typography";
import * as React from "react";

type RecoveryCodesDialogProps = {
  open: boolean;
  codes: string[];
  title?: string;
  onClose: () => void;
};

export default function RecoveryCodesDialog({
  open,
  codes,
  title = "Save your recovery codes",
  onClose,
}: RecoveryCodesDialogProps) {
  const [saved, setSaved] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setSaved(false);
    }
  }, [open, codes]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(codes.join("\n"));
  };

  const handleDownload = () => {
    const blob = new Blob([`${codes.join("\n")}\n`], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "keprix-recovery-codes.txt";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={open} onClose={() => undefined} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2 }}>
        <Alert severity="warning">
          Store these codes somewhere safe. Each code works once if you lose access to your authenticator app.
        </Alert>
        <Box
          component="pre"
          sx={{
            m: 0,
            p: 2,
            bgcolor: "action.hover",
            borderRadius: 1,
            fontFamily: "monospace",
            fontSize: 14,
            whiteSpace: "pre-wrap",
          }}
        >
          {codes.join("\n")}
        </Box>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <Button size="small" variant="outlined" onClick={() => void handleCopy()}>
            Copy codes
          </Button>
          <Button size="small" variant="outlined" onClick={handleDownload}>
            Download .txt
          </Button>
        </Box>
        <FormControlLabel
          control={<Checkbox checked={saved} onChange={(event) => setSaved(event.target.checked)} />}
          label="I saved these recovery codes"
        />
      </DialogContent>
      <DialogActions>
        <Button variant="contained" onClick={onClose} disabled={!saved}>
          Done
        </Button>
      </DialogActions>
    </Dialog>
  );
}
