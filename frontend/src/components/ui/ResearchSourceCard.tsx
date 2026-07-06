"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";
import StatusPill from "@/components/ui/StatusPill";
import type { StatusKey } from "@/theme/tokens/status";

export type ResearchSource = {
  id: string;
  title: string;
  url?: string;
  publisher?: string;
  retrievedAt?: string;
  status?: StatusKey;
};

type ResearchSourceCardProps = {
  source: ResearchSource;
  onOpen?: (id: string) => void;
};

export default function ResearchSourceCard({ source, onOpen }: ResearchSourceCardProps) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1, mb: 1 }}>
          <Typography variant="subtitle1" fontWeight={600}>{source.title}</Typography>
          {source.status ? <StatusPill status={source.status} /> : null}
        </Box>
        {source.publisher ? (
          <Typography variant="body2" color="text.secondary">{source.publisher}</Typography>
        ) : null}
        {source.url ? (
          <Link href={source.url} target="_blank" rel="noreferrer" variant="body2">
            {source.url}
          </Link>
        ) : null}
        {source.retrievedAt ? (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            Retrieved {source.retrievedAt}
          </Typography>
        ) : null}
        {onOpen ? (
          <Box sx={{ mt: 1.5 }}>
            <Link component="button" variant="body2" onClick={() => onOpen(source.id)}>
              View source details
            </Link>
          </Box>
        ) : null}
      </CardContent>
    </Card>
  );
}
