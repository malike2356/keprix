"use client";

import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import { SkeletonList } from "@/components/ui/loading";

export type Citation = {
  id: string;
  label: string;
  href?: string;
  note?: string;
};

type CitationListProps = {
  citations: Citation[];
  loading?: boolean;
  emptyMessage?: string;
};

export default function CitationList({
  citations,
  loading = false,
  emptyMessage = "No citations yet.",
}: CitationListProps) {
  if (loading) {
    return <SkeletonList rows={4} rowHeight={56} />;
  }
  if (citations.length === 0) {
    return <Typography variant="body2" color="text.secondary">{emptyMessage}</Typography>;
  }

  return (
    <List dense>
      {citations.map((citation, index) => (
        <ListItem key={citation.id} alignItems="flex-start" disableGutters>
          <ListItemText
            primary={
              <Box sx={{ display: "flex", gap: 1, alignItems: "baseline" }}>
                <Typography variant="body2" component="span">[{index + 1}]</Typography>
                {citation.href ? (
                  <Link href={citation.href} target="_blank" rel="noreferrer">{citation.label}</Link>
                ) : (
                  <Typography variant="body2">{citation.label}</Typography>
                )}
              </Box>
            }
            secondary={citation.note}
          />
        </ListItem>
      ))}
    </List>
  );
}
