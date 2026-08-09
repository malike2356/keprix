"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import LinearProgress from "@mui/material/LinearProgress";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonChart, SkeletonStatGrid } from "@/components/ui/loading";
import { useCESession } from "@/lib/ce-auth";
import {
  addGlossaryTerm,
  exportFlywheel,
  fetchLocalizationMetrics,
  fetchTopCorrectedTerms,
} from "@/lib/localization-corrections-api";

const DOMAIN_OPTIONS = [
  { value: "borehole_drilling", label: "Borehole drilling" },
  { value: "generic", label: "Generic" },
];

const LANGUAGE_OPTIONS = [
  { code: "ak-GH", label: "Twi (ak-GH)" },
  { code: "en-GH", label: "English (en-GH)" },
  { code: "ee-GH", label: "Ewe (ee-GH)" },
  { code: "ha-GH", label: "Hausa (ha-GH)" },
];

function percentLabel(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

export default function LocalizationMetricsPage() {
  const { user } = useCESession();
  const isAdmin = user?.role === "admin" || user?.role === "owner";

  const { data: metrics, mutate: mutateMetrics } = useSWR(
    isAdmin ? "localization-metrics" : null,
    fetchLocalizationMetrics,
  );

  const [domain, setDomain] = React.useState("borehole_drilling");
  const [languageCode, setLanguageCode] = React.useState("ak-GH");
  const { data: topTerms, mutate: mutateTerms } = useSWR(
    isAdmin ? `localization-top-terms-${domain}-${languageCode}` : null,
    () => fetchTopCorrectedTerms(domain, languageCode),
  );

  const [exportPath, setExportPath] = React.useState("/tmp/keprix-flywheel-export");
  const [glossaryTerm, setGlossaryTerm] = React.useState<{ term: string; translation: string } | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [working, setWorking] = React.useState(false);

  const handleExport = async () => {
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      const result = await exportFlywheel(exportPath);
      setMessage(`Export complete: ${result.sm4t?.total_samples ?? 0} SM4T samples.`);
      await mutateMetrics();
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "Export failed");
    } finally {
      setWorking(false);
    }
  };

  const handleAddGlossary = async () => {
    if (!glossaryTerm || !glossaryTerm.translation.trim()) {
      setError("Enter a translation for the glossary term.");
      return;
    }
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      await addGlossaryTerm(domain, glossaryTerm.term, glossaryTerm.translation.trim());
      setMessage(`Added "${glossaryTerm.term}" to the ${domain} glossary.`);
      setGlossaryTerm(null);
      await mutateTerms();
    } catch (glossaryError) {
      setError(glossaryError instanceof Error ? glossaryError.message : "Glossary update failed");
    } finally {
      setWorking(false);
    }
  };

  if (!isAdmin) {
    return (
      <Box>
        <PageHeader
          title="Localization metrics"
          description="Correction rates, provider accuracy, and training readiness."
          breadcrumbs={[
            { label: "Settings", href: "/settings" },
            { label: "Metrics" },
          ]}
        />
        <Alert severity="warning">Admin access is required to view localization metrics.</Alert>
      </Box>
    );
  }

  const correctionRate = metrics?.correction_rate;
  const coverage = metrics?.coverage;
  const providers = metrics?.provider_accuracy?.providers ?? [];
  const readiness = coverage?.readiness_by_language ?? {};

  return (
    <Box>
      <PageHeader
        title="Localization metrics"
        description="Track correction rates, provider accuracy, and fine-tuning readiness."
        breadcrumbs={[
          { label: "Settings", href: "/settings" },
          { label: "Localization metrics" },
        ]}
        actions={
          <Button component="a" href="/settings/localization/corrections" size="small">
            Review corrections
          </Button>
        }
      />

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      {!metrics ? (
        <Box>
          <SkeletonStatGrid count={3} />
          <Box sx={{ mt: 3 }}>
            <SkeletonChart height={280} />
          </Box>
        </Box>
      ) : (
        <>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" }, mb: 3 }}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="overline" color="text.secondary">
                  Correction rate
                </Typography>
                <Typography variant="h4">{percentLabel(correctionRate?.correction_rate ?? 0)}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {correctionRate?.corrections_approved ?? 0} approved / {correctionRate?.audit_records ?? 0} interactions
                </Typography>
              </CardContent>
            </Card>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="overline" color="text.secondary">
                  Training samples
                </Typography>
                <Typography variant="h4">{coverage?.training_samples_staged ?? 0}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {coverage?.training_samples_exported ?? 0} exported
                </Typography>
              </CardContent>
            </Card>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="overline" color="text.secondary">
                  Total corrections
                </Typography>
                <Typography variant="h4">{coverage?.correction_count ?? 0}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {coverage?.interaction_count ?? 0} audited interactions
                </Typography>
              </CardContent>
            </Card>
          </Box>

          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Provider accuracy
              </Typography>
              {providers.length === 0 ? (
                <Typography color="text.secondary">No provider data yet.</Typography>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Provider</TableCell>
                      <TableCell>Language</TableCell>
                      <TableCell>Month</TableCell>
                      <TableCell align="right">Responses</TableCell>
                      <TableCell align="right">Corrections</TableCell>
                      <TableCell align="right">Rate</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {providers
                      .slice()
                      .sort((a, b) => b.correction_rate - a.correction_rate)
                      .map((row) => (
                        <TableRow
                          key={`${row.provider}-${row.language}-${row.month}`}
                          sx={
                            row.needs_investigation
                              ? {
                                  bgcolor: (theme) =>
                                    alpha(theme.palette.warning.main, theme.palette.mode === "dark" ? 0.16 : 0.12),
                                }
                              : undefined
                          }
                        >
                          <TableCell>{row.provider}</TableCell>
                          <TableCell>{row.language}</TableCell>
                          <TableCell>{row.month || "-"}</TableCell>
                          <TableCell align="right">{row.total_responses ?? "-"}</TableCell>
                          <TableCell align="right">{row.total_corrections ?? "-"}</TableCell>
                          <TableCell align="right">
                            {percentLabel(row.correction_rate)}
                            {row.needs_investigation ? (
                              <Chip size="small" color="warning" label=">10%" sx={{ ml: 1 }} />
                            ) : null}
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Training readiness (500 samples per language)
              </Typography>
              {Object.keys(readiness).length === 0 ? (
                <Typography color="text.secondary">No staged samples yet.</Typography>
              ) : (
                <Box sx={{ display: "grid", gap: 2 }}>
                  {Object.entries(readiness).map(([language, stats]) => {
                    const threshold = stats.threshold || 500;
                    const progress = Math.min(100, (stats.staged_samples / threshold) * 100);
                    return (
                      <Box key={language}>
                        <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                          <Typography variant="body2">{language}</Typography>
                          <Typography variant="body2" color="text.secondary">
                            {stats.staged_samples} / {threshold}
                            {stats.ready_for_export ? " (ready)" : ""}
                          </Typography>
                        </Box>
                        <LinearProgress variant="determinate" value={progress} />
                      </Box>
                    );
                  })}
                </Box>
              )}
              <Box sx={{ display: "flex", gap: 2, mt: 2, flexWrap: "wrap", alignItems: "center" }}>
                <TextField
                  size="small"
                  label="Export path"
                  value={exportPath}
                  onChange={(event) => setExportPath(event.target.value)}
                  sx={{ minWidth: 280 }}
                />
                <Button variant="contained" size="small" disabled={working} onClick={() => void handleExport()}>
                  Export training data
                </Button>
              </Box>
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Most corrected terms
              </Typography>
              <Box sx={{ display: "flex", gap: 2, mb: 2, flexWrap: "wrap" }}>
                <FormControl size="small" sx={{ minWidth: 180 }}>
                  <InputLabel>Domain</InputLabel>
                  <Select label="Domain" value={domain} onChange={(event) => setDomain(event.target.value)}>
                    {DOMAIN_OPTIONS.map((option) => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small" sx={{ minWidth: 160 }}>
                  <InputLabel>Language</InputLabel>
                  <Select
                    label="Language"
                    value={languageCode}
                    onChange={(event) => setLanguageCode(event.target.value)}
                  >
                    {LANGUAGE_OPTIONS.map((lang) => (
                      <MenuItem key={lang.code} value={lang.code}>
                        {lang.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Box>
              {(topTerms?.terms ?? []).length === 0 ? (
                <Typography color="text.secondary">No corrected terms for this domain and language.</Typography>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Term</TableCell>
                      <TableCell align="right">Corrections</TableCell>
                      <TableCell />
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {(topTerms?.terms ?? []).map((row: { term: string; correction_count: number }) => (
                      <TableRow key={row.term}>
                        <TableCell>{row.term}</TableCell>
                        <TableCell align="right">{row.correction_count}</TableCell>
                        <TableCell align="right">
                          <Button
                            size="small"
                            onClick={() => setGlossaryTerm({ term: row.term, translation: "" })}
                          >
                            Add to glossary
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}

      <Dialog open={Boolean(glossaryTerm)} onClose={() => setGlossaryTerm(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Add glossary term</DialogTitle>
        <DialogContent sx={{ pt: 1 }}>
          <TextField
            label="Source term"
            value={glossaryTerm?.term ?? ""}
            fullWidth
            margin="normal"
            InputProps={{ readOnly: true }}
          />
          <TextField
            label="Approved translation"
            value={glossaryTerm?.translation ?? ""}
            onChange={(event) =>
              setGlossaryTerm((current) => (current ? { ...current, translation: event.target.value } : current))
            }
            fullWidth
            margin="normal"
            multiline
            minRows={2}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setGlossaryTerm(null)}>Cancel</Button>
          <Button variant="contained" disabled={working} onClick={() => void handleAddGlossary()}>
            Save to glossary
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
