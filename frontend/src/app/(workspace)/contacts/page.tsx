"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ContactsIcon from "@mui/icons-material/Contacts";
import EmailIcon from "@mui/icons-material/Email";
import PhoneIcon from "@mui/icons-material/Phone";
import { useRouter } from "next/navigation";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonList } from "@/components/ui/loading";
import {
  createContact,
  fetchContacts,
  primaryEmail,
  primaryPhone,
  type Contact,
} from "@/lib/contacts-api";

const SOURCE_FILTERS = ["all", "manual", "google", "microsoft", "carddav", "csv", "vcf"] as const;

export default function ContactsPage() {
  const router = useRouter();

  const [query, setQuery] = React.useState("");
  const [source, setSource] = React.useState<(typeof SOURCE_FILTERS)[number]>("all");
  const [contacts, setContacts] = React.useState<Contact[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [limit, setLimit] = React.useState(100);
  const [createOpen, setCreateOpen] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [form, setForm] = React.useState({
    display_name: "",
    email: "",
    phone: "",
    organisation: "",
    job_title: "",
    notes: "",
    tags: "",
  });

  React.useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("id");
    if (id) router.replace(`/contacts/${id}`);
  }, [router]);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setContacts(
        await fetchContacts({
          q: query || undefined,
          source,
          limit,
          offset: 0,
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load contacts");
    } finally {
      setLoading(false);
    }
  }, [query, source, limit]);

  React.useEffect(() => {
    const timer = setTimeout(() => void load(), 250);
    return () => clearTimeout(timer);
  }, [load]);

  const grouped = React.useMemo(() => {
    const map = new Map<string, Contact[]>();
    for (const contact of contacts) {
      const key = (contact.family_name || contact.display_name || "?")[0]?.toUpperCase() || "#";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(contact);
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [contacts]);

  const onCreate = async () => {
    if (!form.display_name.trim()) {
      setError("Name is required");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await createContact({
        display_name: form.display_name.trim(),
        organisation: form.organisation.trim() || null,
        job_title: form.job_title.trim() || null,
        notes: form.notes.trim() || null,
        emails: form.email.trim()
          ? [{ address: form.email.trim(), label: "work", primary: true }]
          : [],
        phones: form.phone.trim()
          ? [{ number: form.phone.trim(), label: "mobile", primary: true }]
          : [],
        tags: form.tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      });
      setCreateOpen(false);
      setForm({
        display_name: "",
        email: "",
        phone: "",
        organisation: "",
        job_title: "",
        notes: "",
        tags: "",
      });
      router.push(`/contacts/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Contacts"
        description="Directory and dossier: search, edit, tag, sync Google/Outlook/CardDAV, and act with email, call, or WhatsApp."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Contacts", href: "/contacts" },
        ]}
        actions={
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button variant="contained" onClick={() => setCreateOpen(true)}>
              Add contact
            </Button>
            <Button component="a" href="/contacts/sync" variant="outlined">
              Sync settings
            </Button>
            <Button component="a" href="/contacts/preferences" variant="outlined">
              Preferences
            </Button>
          </Stack>
        }
      />

      <TextField
        fullWidth
        size="small"
        placeholder="Search name, email, phone, company..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        sx={{ mb: 1.5 }}
      />

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
        {SOURCE_FILTERS.map((value) => (
          <Chip
            key={value}
            size="small"
            label={value}
            color={source === value ? "primary" : "default"}
            variant={source === value ? "filled" : "outlined"}
            onClick={() => setSource(value)}
          />
        ))}
      </Stack>

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}

      {loading ? (
        <SkeletonList rows={8} rowHeight={64} />
      ) : contacts.length === 0 ? (
        <EmptyState
          title="No contacts yet"
          description="Add a manual contact, import CSV/vCard, or connect Google, Outlook, or CardDAV."
          icon={<ContactsIcon sx={{ fontSize: 48 }} />}
          actionLabel="Add contact"
          onAction={() => setCreateOpen(true)}
        />
      ) : (
        <>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Showing {contacts.length} contact{contacts.length === 1 ? "" : "s"}
          </Typography>
          {grouped.map(([letter, rows]) => (
            <Box key={letter} sx={{ mb: 2 }}>
              <Typography variant="overline" color="text.secondary">
                {letter}
              </Typography>
              <List dense>
                {rows.map((contact) => {
                  const email = primaryEmail(contact);
                  const phone = primaryPhone(contact);
                  return (
                    <ListItemButton
                      key={contact.id}
                      component="a"
                      href={`/contacts/${contact.id}`}
                      sx={{ border: 1, borderColor: "divider", borderRadius: 1, mb: 0.5 }}
                    >
                      <ListItemText
                        primary={
                          <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                            <Typography fontWeight={600}>{contact.display_name}</Typography>
                            <Chip size="small" label={contact.source} variant="outlined" />
                            {(contact.tags || []).slice(0, 3).map((tag) => (
                              <Chip key={tag} size="small" label={tag} />
                            ))}
                          </Box>
                        }
                        secondary={
                          <Box component="span" sx={{ display: "flex", flexDirection: "column", gap: 0.25 }}>
                            {(contact.role || contact.organisation || contact.job_title) && (
                              <span>{contact.role || [contact.job_title, contact.organisation].filter(Boolean).join(" · ")}</span>
                            )}
                            {email ? (
                              <Box component="span" sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                                <EmailIcon sx={{ fontSize: 14 }} />
                                {email}
                              </Box>
                            ) : null}
                            {phone ? (
                              <Box component="span" sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                                <PhoneIcon sx={{ fontSize: 14 }} />
                                {phone}
                              </Box>
                            ) : null}
                          </Box>
                        }
                      />
                    </ListItemButton>
                  );
                })}
              </List>
            </Box>
          ))}
          {contacts.length >= limit ? (
            <Button variant="outlined" onClick={() => setLimit((n) => n + 100)}>
              Show more
            </Button>
          ) : null}
        </>
      )}

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Add contact</DialogTitle>
        <DialogContent>
          <Stack spacing={1.5} sx={{ mt: 1 }}>
            <TextField
              size="small"
              label="Name"
              required
              value={form.display_name}
              onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
            />
            <TextField
              size="small"
              label="Email"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            />
            <TextField
              size="small"
              label="Phone"
              value={form.phone}
              onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
            />
            <TextField
              size="small"
              label="Organisation"
              value={form.organisation}
              onChange={(e) => setForm((f) => ({ ...f, organisation: e.target.value }))}
            />
            <TextField
              size="small"
              label="Job title"
              value={form.job_title}
              onChange={(e) => setForm((f) => ({ ...f, job_title: e.target.value }))}
            />
            <TextField
              size="small"
              label="Tags (comma separated)"
              value={form.tags}
              onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))}
            />
            <TextField
              size="small"
              label="Notes"
              multiline
              minRows={2}
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={busy} onClick={() => void onCreate()}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
