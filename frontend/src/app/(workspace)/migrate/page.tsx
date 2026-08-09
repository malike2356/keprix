"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import {
  applyMigration,
  defaultSelectedIds,
  parseMigration,
  type MigrationManifest,
  validateMigration,
} from "@/lib/migration-api";

const SOURCES = [
  { id: "hermes", label: "Hermes export (.zip)" },
  { id: "openclaw", label: "OpenClaw export (.zip)" },
  { id: "markdown", label: "Markdown notes (.zip)" },
  { id: "generic", label: "Generic manifest (.json or .zip)" },
];

export default function MigratePage() {
  const [source, setSource] = React.useState("hermes");
  const [file, setFile] = React.useState<File | null>(null);
  const [manifest, setManifest] = React.useState<MigrationManifest | null>(null);
  const [selected, setSelected] = React.useState<string[]>([]);
  const [step, setStep] = React.useState(1);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const handleParse = async () => {
    if (!file) {
      setError("Choose an export file first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const parsed = await parseMigration(source, file);
      const validation = await validateMigration(parsed);
      if (!validation.valid) {
        setError(validation.errors.join("; "));
        return;
      }
      setManifest(parsed);
      setSelected(defaultSelectedIds(parsed));
      setStep(2);
      setMessage(`Parsed ${parsed.summary.item_count} items from ${parsed.source.name}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Parse failed");
    } finally {
      setBusy(false);
    }
  };

  const toggleItem = (id: string) => {
    setSelected((current) => (current.includes(id) ? current.filter((value) => value !== id) : [...current, id]));
  };

  const handleApply = async () => {
    if (!manifest) return;
    setBusy(true);
    setError(null);
    try {
      const result = await applyMigration(manifest, selected);
      setStep(4);
      setMessage(`Imported ${result.imported}, skipped ${result.skipped}, failed ${result.failed}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Apply failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Agent migration"
        description="Import memory, skills, and archives from Hermes, OpenClaw, or Markdown notes."
        actions={
          manifest ? (
            <Button component="a" href="/migrate/preview" variant="outlined">
              Open preview page
            </Button>
          ) : null
        }
      />

      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      {message ? <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert> : null}

      {step === 1 ? (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Step 1: Choose source</Typography>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel id="migration-source-label">Source</InputLabel>
              <Select
                labelId="migration-source-label"
                value={source}
                label="Source"
                onChange={(event) => setSource(event.target.value)}
              >
                {SOURCES.map((row) => (
                  <MenuItem key={row.id} value={row.id}>{row.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button variant="outlined" component="label" sx={{ mr: 2 }}>
              Upload export
              <input hidden type="file" accept=".zip,.json" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
            </Button>
            <Typography variant="body2" component="span">{file?.name ?? "No file selected"}</Typography>
            <Box sx={{ mt: 2 }}>
              <Button variant="contained" disabled={busy || !file} onClick={handleParse}>
                Parse and preview
              </Button>
            </Box>
          </CardContent>
        </Card>
      ) : null}

      {manifest && step >= 2 ? (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>Step 2: Review items</Typography>
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
              {Object.entries(manifest.summary.counts_by_kind).map(([kind, count]) => (
                <Chip key={kind} label={`${kind}: ${count}`} />
              ))}
              {manifest.warnings.map((warning, index) => (
                <Chip key={`${warning.message}-${index}`} color="warning" label={warning.message} />
              ))}
            </Box>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox" />
                  <TableCell>Kind</TableCell>
                  <TableCell>Title</TableCell>
                  <TableCell>Confidence</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {manifest.items.map((item) => (
                  <TableRow key={item.id} hover>
                    <TableCell padding="checkbox">
                      <Checkbox checked={selected.includes(item.id)} onChange={() => toggleItem(item.id)} />
                    </TableCell>
                    <TableCell>{item.kind}</TableCell>
                    <TableCell title={item.content}>{item.title}</TableCell>
                    <TableCell>{item.memory_confidence ?? "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Box sx={{ mt: 2, display: "flex", gap: 1 }}>
              <Button variant="outlined" onClick={() => setStep(1)}>Back</Button>
              <Button variant="contained" disabled={busy || selected.length === 0} onClick={handleApply}>
                Apply selected ({selected.length})
              </Button>
            </Box>
          </CardContent>
        </Card>
      ) : null}
    </Box>
  );
}
