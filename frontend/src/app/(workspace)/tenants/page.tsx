"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { createTenant, fetchMyTenants, fetchTenantsAdmin } from "@/lib/parity-api";

export default function TenantsPage() {
  const { data: mine, mutate: mutateMine, error: mineError } = useSWR("tenants-me", fetchMyTenants);
  const { data: all, mutate: mutateAll, error: allError } = useSWR("tenants-admin", fetchTenantsAdmin, {
    shouldRetryOnError: false,
  });
  const [slug, setSlug] = React.useState("");
  const [displayName, setDisplayName] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const onCreate = async () => {
    setBusy(true);
    setError(null);
    try {
      await createTenant({ slug: slug.trim(), display_name: displayName.trim() || slug.trim() });
      setSlug("");
      setDisplayName("");
      await Promise.all([mutateMine(), mutateAll()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader title="Tenants" description="Membership and tenant registry for this Keprix instance." />
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      {mineError ? <Alert severity="warning" sx={{ mb: 2 }}>Could not load /api/tenants/me</Alert> : null}
      <Typography variant="h6" sx={{ mt: 2 }}>My tenants</Typography>
      <Stack spacing={1} sx={{ mt: 1, mb: 3 }}>
        {(mine?.tenants || []).map((tenant) => (
          <Box key={String(tenant.id)} sx={{ borderBottom: 1, borderColor: "divider", py: 1 }}>
            <Typography fontWeight={600}>{String(tenant.display_name || tenant.slug)}</Typography>
            <Typography variant="body2" color="text.secondary">
              {String(tenant.slug)} · {String(tenant.role || "member")} · {String(tenant.id)}
            </Typography>
          </Box>
        ))}
        {!mine?.tenants?.length ? <Typography color="text.secondary">No memberships yet.</Typography> : null}
      </Stack>

      <Typography variant="h6">Create tenant (admin)</Typography>
      {allError ? (
        <Alert severity="info" sx={{ my: 1 }}>Admin list unavailable (admin role required for create/list).</Alert>
      ) : (
        <Stack spacing={1} sx={{ mt: 1, mb: 2 }}>
          {(all?.tenants || []).map((tenant) => (
            <Typography key={String(tenant.id)} variant="body2">
              {String(tenant.slug)} ({String(tenant.status)})
            </Typography>
          ))}
        </Stack>
      )}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mt: 1 }}>
        <TextField size="small" label="Slug" value={slug} onChange={(e) => setSlug(e.target.value)} />
        <TextField size="small" label="Display name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        <Button variant="contained" disabled={busy || !slug.trim()} onClick={() => void onCreate()}>
          Create
        </Button>
      </Stack>
    </Box>
  );
}
