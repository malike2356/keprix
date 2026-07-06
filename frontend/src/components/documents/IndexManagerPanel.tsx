"use client";

import RefreshIcon from "@mui/icons-material/Refresh";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import { fetchDocumentIndexes, inspectDocumentIndex } from "@/lib/documents-api";

export default function IndexManagerPanel() {
  const { data, mutate } = useSWR("document-indexes", () => fetchDocumentIndexes());
  const firstIndex = data?.indexes?.[0]?.index_id;
  const { data: coverage, mutate: refreshCoverage } = useSWR(
    firstIndex ? ["document-index-coverage", firstIndex] : null,
    () => inspectDocumentIndex(firstIndex as string),
  );

  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
          <Typography variant="h6">Index manager</Typography>
          <Button
            size="small"
            startIcon={<RefreshIcon />}
            onClick={() => {
              void mutate();
              void refreshCoverage();
            }}
          >
            Refresh
          </Button>
        </Box>
        <List dense>
          {(data?.indexes ?? []).map((index) => (
            <ListItem key={index.index_id}>
              <ListItemText
                primary={index.name}
                secondary={`${index.documents.length} documents · ${index.index_id.slice(0, 8)}`}
              />
            </ListItem>
          ))}
        </List>
        {coverage ? (
          <Typography variant="caption" color="text.secondary" component="pre" sx={{ whiteSpace: "pre-wrap" }}>
            {JSON.stringify(coverage.coverage, null, 2)}
          </Typography>
        ) : null}
      </CardContent>
    </Card>
  );
}
