"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import {
  fetchContactPreferences,
  updateContactPreferences,
  type ContactPreferences,
} from "@/lib/contacts-api";

export default function ContactsPreferencesPage() {
  const [prefs, setPrefs] = React.useState<ContactPreferences | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setLoading(true);
    fetchContactPreferences()
      .then(setPrefs)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load preferences"))
      .finally(() => setLoading(false));
  }, []);

  const update = async (patch: Partial<ContactPreferences>) => {
    if (!prefs) {
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const next = await updateContactPreferences(patch);
      setPrefs(next);
      setMessage("Preferences saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  };

  if (loading) {
    return (
      <Box>
        <PageHeader
          title="Contact action preferences"
          description="Control how the agent confirms emails and calls."
          breadcrumbs={[
            { label: "Contacts", href: "/contacts" },
            { label: "Preferences" },
          ]}
        />
        <SkeletonDetailPanel fields={3} />
      </Box>
    );
  }

  if (!prefs) {
    return (
      <Box>
        <PageHeader
          title="Contact action preferences"
          description="Control how the agent confirms emails and calls."
          breadcrumbs={[
            { label: "Contacts", href: "/contacts" },
            { label: "Preferences" },
          ]}
        />
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title="Contact action preferences"
        description="Control how the agent confirms emails and calls."
        breadcrumbs={[
          { label: "Contacts", href: "/contacts" },
          { label: "Preferences" },
        ]}
      />
      {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <FormControlLabel
        control={
          <Switch
            checked={prefs.confirm_before_email}
            onChange={(e) => update({ confirm_before_email: e.target.checked })}
          />
        }
        label="Confirm before sending emails"
      />
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, ml: 4 }}>
        When enabled, the agent reads back the draft and waits for approval before sending.
      </Typography>
      <FormControlLabel
        control={
          <Switch
            checked={prefs.read_back_draft}
            onChange={(e) => update({ read_back_draft: e.target.checked })}
          />
        }
        label="Read back email drafts"
      />
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, ml: 4 }}>
        When enabled, the agent shows the full draft in chat before asking to send.
      </Typography>
      <FormControlLabel
        control={
          <Switch
            checked={prefs.confirm_before_call}
            onChange={(e) => update({ confirm_before_call: e.target.checked })}
          />
        }
        label="Confirm before calling"
      />
      <Typography variant="body2" color="text.secondary" sx={{ ml: 4 }}>
        When enabled, the agent confirms the phone number before initiating a call.
      </Typography>
    </Box>
  );
}
