"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { useCESession } from "@/lib/ce-auth";
import {
  VOICE_LANGUAGE_OPTIONS,
  fetchVoiceTemplateCategories,
  fetchVoiceTemplateCoverage,
  fetchVoiceTemplateFallbacks,
  fetchVoiceTemplates,
  saveVoiceTemplateFallback,
  type VoiceTemplate,
  type VoiceTemplateCategory,
} from "@/lib/voice-templates-api";

const WORKSPACE_ID = "default";

type CellState = "approved" | "pending" | "empty";

function cellColor(state: CellState): string {
  if (state === "approved") return "#2e7d32";
  if (state === "pending") return "#ed6c02";
  return "#e0e0e0";
}

function resolveCellState(
  templates: VoiceTemplate[],
  categoryId: string,
  languageCode: string,
): CellState {
  const lang = languageCode.toLowerCase();
  const matches = templates.filter(
    (item) => item.category_id === categoryId && item.language_code === lang && item.workspace_id === WORKSPACE_ID,
  );
  if (matches.some((item) => item.status === "approved")) return "approved";
  if (matches.some((item) => item.status === "pending")) return "pending";
  return "empty";
}

function CoverageGrid({
  categories,
  templates,
}: {
  categories: VoiceTemplateCategory[];
  templates: VoiceTemplate[];
}) {
  const generic = categories.filter((item) => item.domain === "generic");
  return (
    <Box sx={{ overflowX: "auto", mt: 2 }}>
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell>Category</TableCell>
            {VOICE_LANGUAGE_OPTIONS.map((lang) => (
              <TableCell key={lang.code} align="center">
                {lang.label}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {generic.map((category) => (
            <TableRow key={category.id}>
              <TableCell>
                <Typography variant="body2">{category.label}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {category.id}
                </Typography>
              </TableCell>
              {VOICE_LANGUAGE_OPTIONS.map((lang) => {
                const state = resolveCellState(templates, category.id, lang.code);
                return (
                  <TableCell key={`${category.id}-${lang.code}`} align="center">
                    <Tooltip title={state}>
                      <Box
                        sx={{
                          width: 18,
                          height: 18,
                          borderRadius: 0.5,
                          bgcolor: cellColor(state),
                          mx: "auto",
                        }}
                      />
                    </Tooltip>
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
        Green = approved, orange = pending review, grey = no template.
      </Typography>
    </Box>
  );
}

export default function VoiceTemplatesSettingsPage() {
  const { user } = useCESession();
  const isAdmin = user?.role === "admin" || user?.role === "owner";
  const { data: categories = [] } = useSWR("voice-template-categories", () => fetchVoiceTemplateCategories());
  const { data: templates = [], mutate: mutateTemplates } = useSWR("voice-templates-all", () =>
    fetchVoiceTemplates({ workspace_id: WORKSPACE_ID }),
  );
  const { data: coverage = {} } = useSWR("voice-template-coverage", fetchVoiceTemplateCoverage);
  const { data: fallbacks = {}, mutate: mutateFallbacks } = useSWR("voice-template-fallbacks", fetchVoiceTemplateFallbacks);
  const pending = templates.filter((item) => item.status === "pending");

  const [fallbackLang, setFallbackLang] = React.useState("fan-GH");
  const [fallbackTarget, setFallbackTarget] = React.useState("ak-GH");
  const [fallbackMessage, setFallbackMessage] = React.useState<string | null>(null);
  const [fallbackError, setFallbackError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const current = fallbacks[fallbackLang.toLowerCase()];
    if (current) setFallbackTarget(current);
  }, [fallbacks, fallbackLang]);

  const handleSaveFallback = async () => {
    setFallbackError(null);
    setFallbackMessage(null);
    try {
      await saveVoiceTemplateFallback(fallbackLang, fallbackTarget);
      await mutateFallbacks();
      setFallbackMessage("Language fallback saved.");
    } catch (error) {
      setFallbackError(error instanceof Error ? error.message : "Failed to save fallback");
    }
  };

  return (
    <Box>
      <PageHeader
        title="Voice templates"
        description="Pre-recorded phrases for common agent responses; TTS fills in dynamic content when needed."
        actions={
          <Button component={Link} href="/settings/voice-templates/upload" variant="contained">
            Upload template
          </Button>
        }
      />

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Coverage by language
          </Typography>
          {Object.keys(coverage).length === 0 ? (
            <Typography color="text.secondary">No approved templates yet.</Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Language</TableCell>
                  <TableCell>Covered</TableCell>
                  <TableCell>Coverage</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {Object.entries(coverage).map(([lang, row]) => (
                  <TableRow key={lang}>
                    <TableCell>{lang}</TableCell>
                    <TableCell>
                      {row.covered_categories} / {row.total_categories}
                    </TableCell>
                    <TableCell>{row.coverage_pct}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6">Category coverage grid</Typography>
          <CoverageGrid categories={categories} templates={templates} />
        </CardContent>
      </Card>

      {isAdmin ? (
        <Card variant="outlined" sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Language fallback
            </Typography>
            <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", alignItems: "center" }}>
              <FormControl size="small" sx={{ minWidth: 180 }}>
                <InputLabel>Language</InputLabel>
                <Select label="Language" value={fallbackLang} onChange={(event) => setFallbackLang(event.target.value)}>
                  {VOICE_LANGUAGE_OPTIONS.map((lang) => (
                    <MenuItem key={lang.code} value={lang.code}>
                      {lang.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 180 }}>
                <InputLabel>Fallback to</InputLabel>
                <Select
                  label="Fallback to"
                  value={fallbackTarget}
                  onChange={(event) => setFallbackTarget(event.target.value)}
                >
                  {VOICE_LANGUAGE_OPTIONS.map((lang) => (
                    <MenuItem key={lang.code} value={lang.code}>
                      {lang.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button variant="outlined" onClick={handleSaveFallback}>
                Save fallback
              </Button>
            </Box>
            {fallbackMessage ? (
              <Alert severity="success" sx={{ mt: 2 }}>
                {fallbackMessage}
              </Alert>
            ) : null}
            {fallbackError ? (
              <Alert severity="error" sx={{ mt: 2 }}>
                {fallbackError}
              </Alert>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Pending review
          </Typography>
          {!isAdmin ? (
            <Alert severity="info">Admin access is required to approve or reject templates.</Alert>
          ) : pending.length === 0 ? (
            <Typography color="text.secondary">No templates waiting for review.</Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Category</TableCell>
                  <TableCell>Language</TableCell>
                  <TableCell>Transcript</TableCell>
                  <TableCell>Recorded by</TableCell>
                  <TableCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {pending.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{item.category_id}</TableCell>
                    <TableCell>{item.language_code}</TableCell>
                    <TableCell>{item.transcript}</TableCell>
                    <TableCell>{item.recorded_by || "-"}</TableCell>
                    <TableCell>
                      <Button
                        component={Link}
                        href={`/settings/voice-templates/${item.id}`}
                        size="small"
                        onClick={() => mutateTemplates()}
                      >
                        Review
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
