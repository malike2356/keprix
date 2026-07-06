"use client";

import SearchIcon from "@mui/icons-material/Search";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { createDocumentIndex, queryDocuments } from "@/lib/documents-api";

export default function DocumentAgentPanel() {
  const [question, setQuestion] = React.useState("What sources mention Building 3?");
  const [answer, setAnswer] = React.useState<string | null>(null);
  const [citations, setCitations] = React.useState<Array<Record<string, unknown>>>([]);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const onAsk = async () => {
    setBusy(true);
    setError(null);
    try {
      await createDocumentIndex("Workspace docs").catch(() => null);
      const result = await queryDocuments(question);
      setAnswer(result.answer);
      setCitations(result.citations);
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
          <TextField
            label="Question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            size="small"
            multiline
            minRows={2}
          />
          <Button variant="contained" startIcon={<SearchIcon />} onClick={onAsk} disabled={busy}>
            Ask with citations
          </Button>
        </Box>
        {error ? (
          <Typography color="error" variant="body2" sx={{ mt: 2 }}>
            {error}
          </Typography>
        ) : null}
        {answer ? (
          <Typography variant="body2" sx={{ mt: 2, whiteSpace: "pre-wrap" }}>
            {answer}
          </Typography>
        ) : null}
        {citations.length ? (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2">Citations</Typography>
            <Typography variant="caption" component="pre" sx={{ whiteSpace: "pre-wrap" }}>
              {JSON.stringify(citations, null, 2)}
            </Typography>
          </Box>
        ) : null}
      </CardContent>
    </Card>
  );
}
