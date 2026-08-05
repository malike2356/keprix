"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { fetchAccountProfile, updateAccountProfile } from "@/lib/account-api";
import { useCESession } from "@/lib/ce-auth";

const LOCALE_OPTIONS = [
  { value: "en", label: "English" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "es", label: "Spanish" },
  { value: "pt", label: "Portuguese" },
];

const TIMEZONE_OPTIONS = [
  "UTC",
  "Europe/London",
  "Europe/Paris",
  "America/New_York",
  "America/Chicago",
  "America/Los_Angeles",
  "Africa/Accra",
  "Asia/Dubai",
  "Asia/Singapore",
  "Australia/Sydney",
];

function formatMemberSince(createdAt?: number | null): string {
  if (!createdAt) return "Unknown";
  return new Date(createdAt * 1000).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function AccountProfilePage() {
  const { user, refreshUser } = useCESession();
  const { data: profile, mutate } = useSWR("account-profile", fetchAccountProfile);
  const [displayName, setDisplayName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [avatarUrl, setAvatarUrl] = React.useState("");
  const [locale, setLocale] = React.useState("en");
  const [timezone, setTimezone] = React.useState("UTC");
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    if (!profile) return;
    setDisplayName(profile.display_name ?? profile.username ?? "");
    setEmail(profile.email ?? "");
    setAvatarUrl(profile.avatar_url ?? "");
    setLocale(profile.locale ?? "en");
    setTimezone(profile.timezone ?? "UTC");
  }, [profile]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await updateAccountProfile({
        display_name: displayName.trim(),
        email: email.trim(),
        avatar_url: avatarUrl.trim(),
        locale,
        timezone,
      });
      await mutate();
      await refreshUser();
      setMessage("Profile saved.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const readOnlyUsername = profile?.username ?? user?.username ?? "";
  const readOnlyRole = profile?.role ?? user?.role ?? "user";

  return (
    <Box>
      <PageHeader
        title="Account profile"
        description="Update your display name, email, and regional preferences."
        breadcrumbs={[
          { label: "Settings", href: "/settings" },
          { label: "Account", href: "/settings/account/profile" },
          { label: "Profile" },
        ]}
      />

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Account details
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Username: {readOnlyUsername}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Role: {readOnlyRole}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Member since: {formatMemberSince(profile?.created_at)}
          </Typography>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <TextField
            label="Display name"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            fullWidth
            helperText="Shown in the workspace header and shared surfaces."
          />
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            fullWidth
            autoComplete="email"
          />
          <TextField
            label="Avatar URL"
            value={avatarUrl}
            onChange={(event) => setAvatarUrl(event.target.value)}
            fullWidth
            placeholder="https://example.com/avatar.png"
            helperText="Optional image URL for your profile avatar."
          />
          <FormControl fullWidth>
            <InputLabel id="account-locale-label">Locale</InputLabel>
            <Select
              labelId="account-locale-label"
              label="Locale"
              value={locale}
              onChange={(event) => setLocale(event.target.value)}
            >
              {LOCALE_OPTIONS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel id="account-timezone-label">Timezone</InputLabel>
            <Select
              labelId="account-timezone-label"
              label="Timezone"
              value={timezone}
              onChange={(event) => setTimezone(event.target.value)}
            >
              {TIMEZONE_OPTIONS.map((option) => (
                <MenuItem key={option} value={option}>
                  {option}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Box>
            <Button variant="contained" onClick={() => void handleSave()} disabled={saving || !profile}>
              {saving ? "Saving..." : "Save profile"}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
