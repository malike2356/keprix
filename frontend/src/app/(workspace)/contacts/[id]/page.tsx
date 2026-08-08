"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import EmailIcon from "@mui/icons-material/Email";
import PhoneIcon from "@mui/icons-material/Phone";
import WhatsAppIcon from "@mui/icons-material/WhatsApp";
import CalendarMonthIcon from "@mui/icons-material/CalendarMonth";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import * as React from "react";
import NextLink from "next/link";
import { useParams, useRouter } from "next/navigation";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import {
  deleteContact,
  digitsForDial,
  fetchContact,
  fetchContactActivity,
  primaryEmail,
  primaryPhone,
  updateContact,
  whatsappHref,
  type Contact,
  type ContactActivity,
} from "@/lib/contacts-api";

export default function ContactDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [contact, setContact] = React.useState<Contact | null>(null);
  const [activity, setActivity] = React.useState<ContactActivity | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [editing, setEditing] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [form, setForm] = React.useState({
    display_name: "",
    email: "",
    phone: "",
    organisation: "",
    job_title: "",
    notes: "",
    tags: "",
    whatsapp: "",
    telegram: "",
    role: "",
  });

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const row = await fetchContact(params.id);
      setContact(row);
      setForm({
        display_name: row.display_name || "",
        email: primaryEmail(row) || "",
        phone: primaryPhone(row) || "",
        organisation: row.organisation || "",
        job_title: row.job_title || "",
        notes: row.notes || "",
        tags: (row.tags || []).join(", "),
        whatsapp: row.whatsapp || "",
        telegram: row.telegram || "",
        role: row.role || "",
      });
      setActivity(await fetchContactActivity(params.id).catch(() => ({ items: [], counts: { email: 0, meeting: 0, total: 0 } })));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  React.useEffect(() => {
    void load();
  }, [load]);

  const onSave = async () => {
    if (!contact) return;
    setBusy(true);
    setError(null);
    try {
      const tags = form.tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      const payload: Partial<Contact> = {
        tags,
        whatsapp: form.whatsapp.trim() || null,
        telegram: form.telegram.trim() || null,
        role: form.role.trim() || null,
      };
      if (contact.editable) {
        Object.assign(payload, {
          display_name: form.display_name.trim() || contact.display_name,
          organisation: form.organisation.trim() || null,
          job_title: form.job_title.trim() || null,
          notes: form.notes.trim() || null,
          emails: form.email.trim()
            ? [{ address: form.email.trim(), label: "work", primary: true }]
            : contact.emails,
          phones: form.phone.trim()
            ? [{ number: form.phone.trim(), label: "mobile", primary: true }]
            : contact.phones,
        });
      }
      const updated = await updateContact(contact.id, payload);
      setContact(updated);
      setEditing(false);
      setMessage("Contact saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const onDelete = async () => {
    if (!contact?.editable) return;
    if (!window.confirm(`Delete ${contact.display_name}?`)) return;
    setBusy(true);
    try {
      await deleteContact(contact.id);
      router.push("/contacts");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <Box>
        <PageHeader title="Contact" description="Loading dossier" breadcrumbs={[{ label: "Contacts", href: "/contacts" }, { label: "Loading" }]} />
        <SkeletonDetailPanel />
      </Box>
    );
  }

  if (error && !contact) {
    return <Alert severity="error">{error}</Alert>;
  }
  if (!contact) return null;

  const email = primaryEmail(contact);
  const phone = primaryPhone(contact);
  const wa = whatsappHref(contact.whatsapp || phone);
  const tel = digitsForDial(phone);

  return (
    <Box>
      <PageHeader
        title={contact.display_name}
        description={contact.role || contact.organisation || contact.job_title || "Contact dossier"}
        breadcrumbs={[
          { label: "Contacts", href: "/contacts" },
          { label: contact.display_name },
        ]}
        actions={
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {email ? (
              <Button startIcon={<EmailIcon />} variant="contained" href={`mailto:${email}`}>
                Email
              </Button>
            ) : null}
            {tel ? (
              <Button startIcon={<PhoneIcon />} variant="outlined" href={`tel:${tel}`}>
                Call
              </Button>
            ) : null}
            {wa ? (
              <Button startIcon={<WhatsAppIcon />} variant="outlined" href={wa} target="_blank" rel="noreferrer">
                WhatsApp
              </Button>
            ) : null}
            <Button
              startIcon={<CalendarMonthIcon />}
              variant="outlined"
              component={NextLink}
              href={`/vical?guest=${encodeURIComponent(email || contact.display_name)}`}
            >
              Schedule
            </Button>
            <Button
              startIcon={<SmartToyIcon />}
              variant="outlined"
              href={`/chat?prompt=${encodeURIComponent(`Help me follow up with ${contact.display_name}`)}`}
            >
              Ask agent
            </Button>
          </Stack>
        }
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

      <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        <Chip label={contact.source} />
        {(contact.tags || []).map((tag) => (
          <Chip key={tag} label={tag} variant="outlined" />
        ))}
        {!contact.editable ? (
          <Typography variant="body2" color="text.secondary" sx={{ alignSelf: "center" }}>
            Core fields sync from {contact.source}. Tags and messaging channels can still be edited here.
          </Typography>
        ) : null}
      </Stack>

      <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
        <Button size="small" variant={editing ? "outlined" : "contained"} onClick={() => setEditing((v) => !v)}>
          {editing ? "Cancel edit" : "Edit"}
        </Button>
        {contact.editable ? (
          <Button size="small" color="error" variant="outlined" disabled={busy} onClick={() => void onDelete()}>
            Delete
          </Button>
        ) : null}
        {editing ? (
          <Button size="small" variant="contained" disabled={busy} onClick={() => void onSave()}>
            Save
          </Button>
        ) : null}
      </Stack>

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          {editing ? (
            <Stack spacing={1.5}>
              <TextField
                size="small"
                label="Name"
                disabled={!contact.editable}
                value={form.display_name}
                onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
              />
              <TextField
                size="small"
                label="Email"
                disabled={!contact.editable}
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              />
              <TextField
                size="small"
                label="Phone"
                disabled={!contact.editable}
                value={form.phone}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
              />
              <TextField
                size="small"
                label="Organisation"
                disabled={!contact.editable}
                value={form.organisation}
                onChange={(e) => setForm((f) => ({ ...f, organisation: e.target.value }))}
              />
              <TextField
                size="small"
                label="Job title"
                disabled={!contact.editable}
                value={form.job_title}
                onChange={(e) => setForm((f) => ({ ...f, job_title: e.target.value }))}
              />
              <TextField
                size="small"
                label="Role label"
                value={form.role}
                onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
              />
              <TextField
                size="small"
                label="WhatsApp"
                value={form.whatsapp}
                onChange={(e) => setForm((f) => ({ ...f, whatsapp: e.target.value }))}
              />
              <TextField
                size="small"
                label="Telegram"
                value={form.telegram}
                onChange={(e) => setForm((f) => ({ ...f, telegram: e.target.value }))}
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
                minRows={3}
                disabled={!contact.editable}
                value={form.notes}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              />
            </Stack>
          ) : (
            <Stack spacing={1}>
              {email ? <Typography>Email: {email}</Typography> : null}
              {phone ? <Typography>Phone: {phone}</Typography> : null}
              {contact.whatsapp ? <Typography>WhatsApp: {contact.whatsapp}</Typography> : null}
              {contact.telegram ? <Typography>Telegram: {contact.telegram}</Typography> : null}
              {contact.organisation ? <Typography>Organisation: {contact.organisation}</Typography> : null}
              {contact.job_title ? <Typography>Title: {contact.job_title}</Typography> : null}
              {contact.notes ? (
                <Typography sx={{ whiteSpace: "pre-wrap", mt: 1 }}>{contact.notes}</Typography>
              ) : (
                <Typography color="text.secondary">No notes yet.</Typography>
              )}
            </Stack>
          )}
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Activity
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
            {activity?.counts.total ?? 0} matched · {activity?.counts.email ?? 0} email · {activity?.counts.meeting ?? 0} meeting
          </Typography>
          <Divider sx={{ mb: 1.5 }} />
          {(activity?.items || []).length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No matched email or calendar activity yet. Connect mailbox/calendar and message this contact to populate the timeline.
            </Typography>
          ) : (
            <Stack spacing={1}>
              {(activity?.items || []).map((item) => (
                <Box key={`${item.kind}-${item.id}`} sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.25 }}>
                  <Stack direction="row" justifyContent="space-between" gap={1}>
                    <Typography variant="body2" fontWeight={600}>
                      {item.title}
                    </Typography>
                    <Chip size="small" label={item.kind} />
                  </Stack>
                  <Typography variant="caption" color="text.secondary" display="block">
                    {item.subtitle}
                    {item.at ? ` · ${new Date(item.at).toLocaleString()}` : ""}
                  </Typography>
                  {item.href ? (
                    <Button size="small" component={NextLink} href={item.href} sx={{ mt: 0.5, px: 0 }}>
                      Open
                    </Button>
                  ) : null}
                </Box>
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
