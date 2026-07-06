"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { fetchMigrationHistory } from "@/lib/migration-api";

export default function MigratePreviewPage() {
  const { data, error } = useSWR("migration-history", () => fetchMigrationHistory());
  const items = data?.items ?? [];

  return (
    <Box>
      <PageHeader
        title="Migration history"
        description="Past agent migrations for this workspace."
        actions={
          <Button component={Link} href="/migrate" variant="contained">
            New migration
          </Button>
        }
      />
      {error ? <Alert severity="error">Could not load migration history.</Alert> : null}
      <Card>
        <CardContent>
          {items.length === 0 ? (
            <Typography variant="body2">No migrations recorded yet.</Typography>
          ) : (
            items.map((row, index) => (
              <Box key={String(row.recorded_at ?? index)} sx={{ mb: 2 }}>
                <Typography variant="subtitle1">
                  {String((row.source as { name?: string } | undefined)?.name ?? "Unknown source")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {String(row.recorded_at ?? "")}
                </Typography>
              </Box>
            ))
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
