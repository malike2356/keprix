"use client";

import * as React from "react";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import { SnackbarFeedback, useSnackbar } from "@/components/ui/SnackbarFeedback";
import { createAdminUser } from "@/lib/admin-pages-api";

type UserFormDialogProps = {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
};

export default function UserFormDialog({ open, onClose, onSaved }: UserFormDialogProps) {
  const { state, show, close } = useSnackbar();
  const [username, setUsername] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [role, setRole] = React.useState("user");
  const [password, setPassword] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (!open) {
      setUsername("");
      setEmail("");
      setRole("user");
      setPassword("");
    }
  }, [open]);

  const handleSubmit = async () => {
    if (!username.trim() || !password.trim()) {
      show("Username and password are required.", "error");
      return;
    }
    setBusy(true);
    try {
      await createAdminUser({
        username: username.trim(),
        email: email.trim() || undefined,
        role,
        password,
      });
      show("User created");
      onSaved();
    } catch (err) {
      show(err instanceof Error ? err.message : "Failed to create user", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
        <DialogTitle>Invite user</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            label="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            fullWidth
          />
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            fullWidth
          />
          <TextField select label="Role" value={role} onChange={(e) => setRole(e.target.value)} fullWidth>
            <MenuItem value="admin">Admin</MenuItem>
            <MenuItem value="user">Member</MenuItem>
            <MenuItem value="viewer">Viewer</MenuItem>
          </TextField>
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button variant="contained" onClick={() => void handleSubmit()} disabled={busy}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
      <SnackbarFeedback state={state} onClose={close} />
    </>
  );
}
