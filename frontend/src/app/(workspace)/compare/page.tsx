"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import Tab from "@mui/material/Tab";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonBlock, SkeletonStatGrid } from "@/components/ui/loading";
import {
  fetchCompareHistory,
  fetchCompareLeaderboard,
  fetchCompareModels,
  startComparison,
  voteComparison,
  type CompareHistoryEntry,
  type CompareLeaderboard,
  type CompareModel,
} from "@/lib/compare-api";


function ModelPicker({
  label,
  models,
  value,
  onChange,
  disabled,
  excludeId,
}: {
  label: string;
  models: CompareModel[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  excludeId?: string;
}) {
  const options = models.filter((item) => item.id !== excludeId);

  return (
    <FormControl fullWidth disabled={disabled}>
      <InputLabel id={`${label}-label`}>{label}</InputLabel>
      <Select
        labelId={`${label}-label`}
        label={label}
        value={value}
        onChange={(event) => onChange(String(event.target.value))}
      >
        {options.map((item) => (
          <MenuItem key={item.id} value={item.id}>
            <Chip size="small" label={item.provider} sx={{ mr: 1 }} />
            {item.label || item.name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}

export default function ComparePage() {
  const [tab, setTab] = React.useState(0);
  const [prompt, setPrompt] = React.useState("");
  const [randomModels, setRandomModels] = React.useState(true);
  const [modelA, setModelA] = React.useState("");
  const [modelB, setModelB] = React.useState("");
  const [responseA, setResponseA] = React.useState("");
  const [responseB, setResponseB] = React.useState("");
  const [latencyA, setLatencyA] = React.useState<number | null>(null);
  const [latencyB, setLatencyB] = React.useState<number | null>(null);
  const [comparisonId, setComparisonId] = React.useState<string | null>(null);
  const [revealedA, setRevealedA] = React.useState<string | null>(null);
  const [revealedB, setRevealedB] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [voting, setVoting] = React.useState(false);
  const [voted, setVoted] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [history, setHistory] = React.useState<CompareHistoryEntry[]>([]);
  const [leaderboard, setLeaderboard] = React.useState<CompareLeaderboard>({ pairs: [], models: [] });

  const { data: models = [], isLoading: modelsLoading } = useSWR("compare-models", fetchCompareModels);

  React.useEffect(() => {
    if (!models.length) {
      return;
    }
    if (!modelA) {
      setModelA(models[0].id);
    }
    if (!modelB) {
      setModelB(models[Math.min(1, models.length - 1)].id);
    }
  }, [modelA, modelB, models]);

  React.useEffect(() => {
    if (tab === 1 || tab === 2) {
      fetchCompareLeaderboard().then(setLeaderboard);
    }
    if (tab === 3) {
      fetchCompareHistory().then(setHistory);
    }
  }, [tab]);

  const resetSession = () => {
    setComparisonId(null);
    setResponseA("");
    setResponseB("");
    setLatencyA(null);
    setLatencyB(null);
    setRevealedA(null);
    setRevealedB(null);
    setVoted(false);
    setError(null);
  };

  const handleStart = async () => {
    if (!prompt.trim()) {
      return;
    }
    if (!randomModels && (!modelA || !modelB || modelA === modelB)) {
      setError("Choose two different models or enable random selection.");
      return;
    }
    setLoading(true);
    resetSession();
    try {
      const result = await startComparison({
        prompt: prompt.trim(),
        modelA: randomModels ? undefined : modelA,
        modelB: randomModels ? undefined : modelB,
        randomModels,
      });
      setComparisonId(result.comparison_id);
      setResponseA(result.response_a);
      setResponseB(result.response_b);
      setLatencyA(result.latency_ms_a);
      setLatencyB(result.latency_ms_b);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Comparison failed");
    } finally {
      setLoading(false);
    }
  };

  const handleVote = async (winner: "a" | "b" | "tie") => {
    if (!comparisonId || voted) {
      return;
    }
    setVoting(true);
    setError(null);
    try {
      const result = await voteComparison(comparisonId, winner);
      setRevealedA(result.model_a);
      setRevealedB(result.model_b);
      setVoted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Vote failed");
    } finally {
      setVoting(false);
    }
  };

  const hasResponses = Boolean(responseA || responseB);
  const canStart =
    prompt.trim().length > 0 &&
    !loading &&
    (randomModels ? models.length >= 2 : Boolean(modelA && modelB && modelA !== modelB));

  return (
    <Box>
      <PageHeader
        title="Compare Models"
        description="Blind A/B evaluation using your configured LLM providers. Vote before model names are revealed."
        breadcrumbs={[
          { label: "Workspace", href: "/launcher" },
          { label: "Compare", href: "/compare" },
        ]}
      />

      <Tabs value={tab} onChange={(_e, value) => setTab(value)} sx={{ mb: 3 }}>
        <Tab label="Compare" />
        <Tab label="Pair rankings" />
        <Tab label="Model rankings" />
        <Tab label="History" />
      </Tabs>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {tab === 0 && (
        <>
          {modelsLoading ? (
            <Box sx={{ mb: 2 }}>
              <SkeletonStatGrid count={2} />
            </Box>
          ) : models.length < 2 ? (
            <Alert severity="warning" sx={{ mb: 2 }}>
              Configure at least two LLM providers in Settings before running comparisons.
            </Alert>
          ) : null}

          <TextField
            label="Prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            fullWidth
            multiline
            minRows={3}
            sx={{ mb: 2 }}
            placeholder="Enter the same prompt for both models"
          />

          <FormControlLabel
            control={
              <Switch
                checked={randomModels}
                onChange={(event) => setRandomModels(event.target.checked)}
              />
            }
            label="Pick two random configured models"
            sx={{ mb: 2, display: "block" }}
          />

          {!randomModels && (
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
                gap: 2,
                mb: 2,
              }}
            >
              <ModelPicker
                label="Model A"
                models={models}
                value={modelA}
                onChange={setModelA}
                excludeId={modelB}
                disabled={modelsLoading}
              />
              <ModelPicker
                label="Model B"
                models={models}
                value={modelB}
                onChange={setModelB}
                excludeId={modelA}
                disabled={modelsLoading}
              />
            </Box>
          )}

          <Button variant="contained" disabled={!canStart} onClick={handleStart} sx={{ mb: 3 }}>
            {loading ? "Generating responses..." : "Start comparison"}
          </Button>

          {loading ? (
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
                gap: 2,
                mb: 3,
              }}
            >
              <SkeletonBlock height={240} />
              <SkeletonBlock height={240} />
            </Box>
          ) : null}

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
              gap: 2,
              mb: 3,
            }}
          >
            <Card>
              <CardContent>
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
                  <Typography variant="overline" color="text.secondary">
                    Response A
                    {voted && revealedA ? ` (${revealedA})` : ""}
                  </Typography>
                  {latencyA !== null ? (
                    <Chip size="small" label={`${latencyA} ms`} variant="outlined" />
                  ) : null}
                </Box>
                <Typography variant="body2" sx={{ mt: 2, minHeight: 200, whiteSpace: "pre-wrap" }}>
                  {hasResponses
                    ? responseA
                    : "Model output will appear here after you start a comparison session."}
                </Typography>
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
                  <Typography variant="overline" color="text.secondary">
                    Response B
                    {voted && revealedB ? ` (${revealedB})` : ""}
                  </Typography>
                  {latencyB !== null ? (
                    <Chip size="small" label={`${latencyB} ms`} variant="outlined" />
                  ) : null}
                </Box>
                <Typography variant="body2" sx={{ mt: 2, minHeight: 200, whiteSpace: "pre-wrap" }}>
                  {hasResponses
                    ? responseB
                    : "Model output will appear here after you start a comparison session."}
                </Typography>
              </CardContent>
            </Card>
          </Box>

          <ButtonGroup variant="outlined" fullWidth sx={{ maxWidth: 480 }} disabled={!hasResponses || voting || voted}>
            <Button onClick={() => handleVote("a")}>A wins</Button>
            <Button onClick={() => handleVote("tie")}>Tie</Button>
            <Button onClick={() => handleVote("b")}>B wins</Button>
          </ButtonGroup>

          {voted && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Vote recorded. Model names are revealed above and saved to history.
            </Typography>
          )}
        </>
      )}

      {tab === 1 && (
        <Card>
          <CardContent>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Model A</TableCell>
                  <TableCell>Model B</TableCell>
                  <TableCell align="right">Comparisons</TableCell>
                  <TableCell align="right">A win %</TableCell>
                  <TableCell align="right">B win %</TableCell>
                  <TableCell align="right">Tie %</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {leaderboard.pairs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6}>
                      <Typography variant="body2" color="text.secondary">
                        No pair rankings yet. Run comparisons and vote to populate rankings.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  leaderboard.pairs.map((row) => (
                    <TableRow key={`${row.model_a}-${row.model_b}`}>
                      <TableCell>{row.model_a}</TableCell>
                      <TableCell>{row.model_b}</TableCell>
                      <TableCell align="right">{row.comparisons}</TableCell>
                      <TableCell align="right">{row.a_win_rate_pct}%</TableCell>
                      <TableCell align="right">{row.b_win_rate_pct}%</TableCell>
                      <TableCell align="right">{row.tie_rate_pct}%</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {tab === 2 && (
        <Card>
          <CardContent>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Model</TableCell>
                  <TableCell align="right">Comparisons</TableCell>
                  <TableCell align="right">Wins</TableCell>
                  <TableCell align="right">Losses</TableCell>
                  <TableCell align="right">Ties</TableCell>
                  <TableCell align="right">Win %</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {leaderboard.models.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6}>
                      <Typography variant="body2" color="text.secondary">
                        No model rankings yet.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  leaderboard.models.map((row) => (
                    <TableRow key={row.model_id}>
                      <TableCell>{row.model_id}</TableCell>
                      <TableCell align="right">{row.comparisons}</TableCell>
                      <TableCell align="right">{row.wins}</TableCell>
                      <TableCell align="right">{row.losses}</TableCell>
                      <TableCell align="right">{row.ties}</TableCell>
                      <TableCell align="right">{row.win_rate_pct}%</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {tab === 3 && (
        <Card>
          <CardContent>
            {history.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No comparison history yet.
              </Typography>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Prompt</TableCell>
                    <TableCell>Models</TableCell>
                    <TableCell>Winner</TableCell>
                    <TableCell>Latency</TableCell>
                    <TableCell>Date</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {history.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell>{entry.prompt}</TableCell>
                      <TableCell>
                        {entry.model_a} vs {entry.model_b}
                      </TableCell>
                      <TableCell>{entry.winner || "pending"}</TableCell>
                      <TableCell>
                        {entry.latency_ms_a != null && entry.latency_ms_b != null
                          ? `${entry.latency_ms_a} / ${entry.latency_ms_b} ms`
                          : "-"}
                      </TableCell>
                      <TableCell>{new Date(entry.created_at).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
