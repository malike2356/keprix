"use client";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

export type MeshRelatedLink = {
  label: string;
  href: string;
};

export function buildVicalRelatedLinks(input: {
  bookingId?: string | null;
  workspaceEventId?: string | null;
  contactId?: string | null;
  publicBookPath?: string | null;
}): MeshRelatedLink[] {
  const links: MeshRelatedLink[] = [];
  if (input.workspaceEventId) {
    links.push({ label: "Open calendar event", href: `/calendar?event=${encodeURIComponent(input.workspaceEventId)}` });
  }
  if (input.contactId) {
    links.push({ label: "Open contact", href: `/contacts?id=${encodeURIComponent(input.contactId)}` });
  }
  if (input.bookingId) {
    links.push({ label: "Open booking", href: `/vical?booking=${encodeURIComponent(input.bookingId)}` });
  }
  if (input.publicBookPath) {
    links.push({ label: "Public book link", href: input.publicBookPath });
  }
  return links;
}

export default function MeshRelatedLinks({ links }: { links: MeshRelatedLink[] }) {
  if (!links.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        No related links yet. Confirm a booking to bridge the calendar event.
      </Typography>
    );
  }
  return (
    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
      {links.map((link) => (
        <Button key={link.href + link.label} size="small" href={link.href} component="a" variant="outlined">
          {link.label}
        </Button>
      ))}
    </Stack>
  );
}
