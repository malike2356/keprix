"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import EmailIcon from "@mui/icons-material/Email";
import PhoneIcon from "@mui/icons-material/Phone";
import * as React from "react";
import { useParams } from "next/navigation";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import { ceApi } from "@/lib/ce-api";
import type { Contact } from "@/lib/contacts-api";

export default function ContactDetailPage() {
  const params = useParams<{ id: string }>();
  const [contact, setContact] = React.useState<Contact | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setLoading(true);
    ceApi(`/api/contacts/${params.id}`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Contact not found");
        }
        setContact(await response.json());
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Load failed"))
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) {
    return (
      <Box>
        <PageHeader
          title="Contact"
          description="Contact details"
          breadcrumbs={[
            { label: "Contacts", href: "/contacts" },
            { label: "Loading" },
          ]}
        />
        <SkeletonDetailPanel />
      </Box>
    );
  }

  if (error) {
    return <Typography color="error">{error}</Typography>;
  }
  if (!contact) {
    return null;
  }

  const primaryEmail = contact.emails.find((e) => e.primary)?.address || contact.emails[0]?.address;
  const primaryPhone = contact.phones.find((p) => p.primary)?.number || contact.phones[0]?.number;

  return (
    <Box>
      <PageHeader
        title={contact.display_name}
        description={contact.organisation || contact.job_title || "Contact details"}
        breadcrumbs={[
          { label: "Contacts", href: "/contacts" },
          { label: contact.display_name },
        ]}
        actions={
          <>
            <Button
              startIcon={<EmailIcon />}
              variant="contained"
              href={`/chat?prompt=${encodeURIComponent(`Email ${contact.display_name}`)}`}
              sx={{ mr: 1 }}
            >
              Email
            </Button>
            <Button
              startIcon={<PhoneIcon />}
              variant="outlined"
              href={`/chat?prompt=${encodeURIComponent(`Call ${contact.display_name}`)}`}
            >
              Call
            </Button>
          </>
        }
      />
      <Chip label={contact.source} sx={{ mb: 2 }} />
      {!contact.editable && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Edit this contact at the source ({contact.source}).
        </Typography>
      )}
      {primaryEmail && <Typography sx={{ mb: 1 }}>Email: {primaryEmail}</Typography>}
      {primaryPhone && <Typography sx={{ mb: 1 }}>Phone: {primaryPhone}</Typography>}
      {contact.notes && <Typography sx={{ mt: 2 }}>{contact.notes}</Typography>}
    </Box>
  );
}
