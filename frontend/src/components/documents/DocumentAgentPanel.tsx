"use client";

import SearchIcon from "@mui/icons-material/Search";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { createDocumentIndex, fetchDocumentIndexes, queryDocuments } from "@/lib/documents-api";

export default function DocumentAgentPanel() {
  const { data } = useSWR("document-indexes", () => fetchDocumentIndexes());
  const indexes = data?.indexes ?? [];
  const [indexId, setIndexId] = React.useState("");
  const [question, setQuestion] = React.useState("What are the key points in my documents?");
  const [answer, setAnswer] = React.useState<string | null>(null);
  const [citations, setCitations] = React.useState<Array<Record<string, unknown>>>([]);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!indexId && indexes[0]?.index_id) {
      setIndexId(indexes[0].index_id);
    }
  }, [indexes, indexId]);

  const onAsk = async () => {
    setBusy(true);
    setError(null);
    try {
      let activeIndex = indexId;
      if (!activeIndex) {
        const created = await createDocumentIndex("Workspace docs");
        activeIndex = created.index_id;
        setIndexId(activeIndex);
      }
      const result = await queryDocuments(question, activeIndex);
      setAnswer(result.answer);
      setCitations(result.citations as Array<Record<string, unknown>>);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Document agent
        </Typography>
        <Box sx={{ display: "grid", gap: 2 }}>
          <FormControl fullWidth size="small">
            <InputLabel id="doc-index-label">Index</InputLabel>
            <Select
              labelId="doc-index-label"
              label="Index"
              value={indexId}
              onChange={(e) => setIndexId(String(e.target.value))}
            >
              {indexes.map((index) => (
                <MenuItem key={index.index_id} value={index.index_id}>
                  {index.name} ({index.documents.length})
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="Question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            size="small"
            multiline
            minRows={2}
          />
          <Button variant="contained" startIcon={<SearchIcon />} onClick={() => void onAsk()} disabled={busy}>
            Ask
          </Button>
          {error ? <Alert severity="error">{error}</Alert> : null}
          {answer ? (
            <Box>
              <Typography variant="subtitle2">Answer</Typography>
              <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                {answer}
              </Typography>
              {citations.length ? (
                <Box sx={{ mt: 1 }}>
                  <StructuredDataView value={citations} emptyLabel="No citations" />
                </Box>
              ) : null}
            </Box>
          ) : null}
        </Box>
      </CardContent>
    </Card>
  );
}
