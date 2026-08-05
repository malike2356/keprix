"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ContactsIcon from "@mui/icons-material/Contacts";
import EmailIcon from "@mui/icons-material/Email";
import PhoneIcon from "@mui/icons-material/Phone";
import NextLink from "next/link";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonList } from "@/components/ui/loading";
import { fetchContacts, type Contact } from "@/lib/contacts-api";

export default function ContactsPage() {
  const [query, setQuery] = React.useState("");
  const [contacts, setContacts] = React.useState<Contact[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(async (q?: string) => {
    setLoading(true);
    setError(null);
    try {
      setContacts(await fetchContacts(q));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load contacts");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  React.useEffect(() => {
    const timer = setTimeout(() => load(query || undefined), 250);
    return () => clearTimeout(timer);
  }, [query, load]);

  const grouped = React.useMemo(() => {
    const map = new Map<string, Contact[]>();
    for (const contact of contacts) {
      const key = (contact.family_name || contact.display_name || "?")[0]?.toUpperCase() || "#";
      if (!map.has(key)) {
        map.set(key, []);
      }
      map.get(key)!.push(contact);
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [contacts]);

  return (
    <Box>
      <PageHeader
        title="Contacts"
        description="Search people and start email or call actions from the agent."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Contacts", href: "/contacts" },
        ]}
        actions={
          <>
            <Button component={NextLink} href="/contacts/sync" variant="outlined" sx={{ mr: 1 }}>
              Sync settings
            </Button>
            <Button component={NextLink} href="/contacts/preferences" variant="outlined">
              Preferences
            </Button>
          </>
        }
      />
      <TextField
        fullWidth
        size="small"
        placeholder="Search contacts..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        sx={{ mb: 2 }}
      />
      {error && (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}
      {loading ? (
        <SkeletonList rows={8} rowHeight={64} />
      ) : contacts.length === 0 ? (
        <EmptyState
          title="No contacts yet"
          description="Import a vCard or CSV file, or connect Google or Outlook sync."
          icon={<ContactsIcon sx={{ fontSize: 48 }} />}
          actionLabel="Open sync settings"
          onAction={() => {
            window.location.href = "/contacts/sync";
          }}
        />
      ) : (
        grouped.map(([letter, rows]) => (
          <Box key={letter} sx={{ mb: 2 }}>
            <Typography variant="overline" color="text.secondary">
              {letter}
            </Typography>
            <List dense>
              {rows.map((contact) => {
                const primaryEmail = contact.emails.find((e) => e.primary)?.address || contact.emails[0]?.address;
                const primaryPhone = contact.phones.find((p) => p.primary)?.number || contact.phones[0]?.number;
                return (
                  <ListItemButton
                    key={contact.id}
                    component={NextLink}
                    href={`/contacts/${contact.id}`}
                    sx={{ border: 1, borderColor: "divider", borderRadius: 1, mb: 0.5 }}
                  >
                    <ListItemText
                      primary={
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                          <Typography fontWeight={600}>{contact.display_name}</Typography>
                          <Chip size="small" label={contact.source} variant="outlined" />
                        </Box>
                      }
                      secondary={
                        <Box component="span" sx={{ display: "flex", flexDirection: "column", gap: 0.25 }}>
                          {contact.organisation && <span>{contact.organisation}</span>}
                          {primaryEmail && (
                            <Box component="span" sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                              <EmailIcon sx={{ fontSize: 14 }} />
                              {primaryEmail}
                            </Box>
                          )}
                          {primaryPhone && (
                            <Box component="span" sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                              <PhoneIcon sx={{ fontSize: 14 }} />
                              {primaryPhone}
                            </Box>
                          )}
                        </Box>
                      }
                    />
                  </ListItemButton>
                );
              })}
            </List>
          </Box>
        ))
      )}
    </Box>
  );
}
