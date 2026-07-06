"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import * as React from "react";
import {
  createZoteroLiteratureNotes,
  exportZoteroBibliography,
  fetchProjectCitations,
  type CitationRecord,
} from "@/lib/research-workspace-api";

type Props = {
  projectId: string | null;
  vaultId: string | null;
};

export default function CitationPicker({ projectId, vaultId }: Props) {
  const [citations, setCitations] = React.useState<CitationRecord[]>([]);
  const [selected, setSelected] = React.useState<string[]>([]);
  const [bibFormat, setBibFormat] = React.useState<"markdown" | "bibtex" | "csl-json" | "report">("report");
  const [preview, setPreview] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    if (!projectId) {
      setCitations([]);
      return;
    }
    try {
      const payload = await fetchProjectCitations(projectId);
      setCitations(payload.items);
    } catch {
      setCitations([]);
    }
  }, [projectId]);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const toggle = (key: string) => {
    setSelected((current) =>
      current.includes(key) ? current.filter((item) => item !== key) : [...current, key],
    );
  };

  const createNotes = async () => {
    if (!projectId) return;
    setError(null);
    try {
      const keys = selected.length ? selected : citations.map((item) => item.citation_key);
      const result = await createZoteroLiteratureNotes(projectId, {
        citation_keys: keys,
        vault_id: vaultId || undefined,
      });
      setMessage(`Created ${result.notes.length} literature notes.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Literature note creation failed");
    }
  };

  const exportBibliography = async () => {
    if (!projectId) return;
    setError(null);
    try {
      const result = await exportZoteroBibliography(projectId, {
        format: bibFormat,
        citation_keys: selected.length ? selected : undefined,
      });
      setPreview(result.content);
      setMessage(`Exported ${result.count} citations as ${result.format}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bibliography export failed");
    }
  };

  if (!projectId) {
    return (
      <Typography variant="body2" color="text.secondary">
        Select a project to pick citations.
      </Typography>
    );
  }

  return (
    <Box sx={{ display: "grid", gap: 1.5 }}>
      <Typography variant="subtitle2">Citation picker</Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
        {citations.map((item) => (
          <Chip
            key={item.citation_key}
            size="small"
            label={`${item.citation_key}: ${item.title}`}
            color={selected.includes(item.citation_key) ? "primary" : "default"}
            onClick={() => toggle(item.citation_key)}
            variant={selected.includes(item.citation_key) ? "filled" : "outlined"}
          />
        ))}
        {!citations.length ? (
          <Typography variant="caption" color="text.secondary">
            Import or sync citations first.
          </Typography>
        ) : null}
      </Box>
      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
        <Button size="small" variant="outlined" onClick={createNotes} disabled={!citations.length}>
          Create literature notes
        </Button>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="bib-format-label">Bibliography</InputLabel>
          <Select
            labelId="bib-format-label"
            label="Bibliography"
            value={bibFormat}
            onChange={(e) => setBibFormat(e.target.value as typeof bibFormat)}
          >
            <MenuItem value="report">Report section</MenuItem>
            <MenuItem value="markdown">Markdown</MenuItem>
            <MenuItem value="bibtex">BibTeX</MenuItem>
            <MenuItem value="csl-json">CSL JSON</MenuItem>
          </Select>
        </FormControl>
        <Button size="small" variant="outlined" onClick={exportBibliography} disabled={!citations.length}>
          Export bibliography
        </Button>
      </Box>
      {preview ? (
        <Typography
          component="pre"
          variant="caption"
          sx={{ whiteSpace: "pre-wrap", bgcolor: "action.hover", p: 1, borderRadius: 1 }}
        >
          {preview}
        </Typography>
      ) : null}
      {message ? (
        <Typography variant="body2" color="text.secondary">
          {message}
        </Typography>
      ) : null}
      {error ? (
        <Typography variant="body2" color="error">
          {error}
        </Typography>
      ) : null}
    </Box>
  );
}
