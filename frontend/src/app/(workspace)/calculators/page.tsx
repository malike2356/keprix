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
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";

type Calculator = { slug: string; label: string; description: string };

export default function CalculatorsPage() {
  const [calculators, setCalculators] = React.useState<Calculator[]>([]);
  const [strategy, setStrategy] = React.useState("");
  const [inputs, setInputs] = React.useState("{}");
  const [result, setResult] = React.useState<unknown>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [running, setRunning] = React.useState(false);

  React.useEffect(() => {
    fetch("/api/property/calculators", { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Unable to load calculators");
        return response.json() as Promise<{ calculators: Calculator[] }>;
      })
      .then((payload) => {
        setCalculators(payload.calculators);
        setStrategy(payload.calculators[0]?.slug ?? "");
      })
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Unable to load calculators"));
  }, []);

  const selected = calculators.find((item) => item.slug === strategy);
  const run = async () => {
    setError(null);
    setResult(null);
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(inputs) as Record<string, unknown>;
    } catch {
      setError("Inputs must be valid JSON.");
      return;
    }
    setRunning(true);
    try {
      const response = await fetch(`/api/property/calculators/${encodeURIComponent(strategy)}/run`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ inputs: parsed }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail?.message ?? "Calculator run failed");
      setResult(payload);
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "Calculator run failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: 1100, mx: "auto" }}>
      <PageHeader title="Property calculators" description="Offline, deterministic investment modelling with workspace-controlled assumptions." />
      <Stack spacing={2} sx={{ mt: 3 }}>
        {error && <Alert severity="error">{error}</Alert>}
        <Card variant="outlined">
          <CardContent>
            <Stack spacing={2}>
              <FormControl fullWidth>
                <InputLabel id="calculator-strategy-label">Strategy</InputLabel>
                <Select labelId="calculator-strategy-label" label="Strategy" value={strategy} onChange={(event) => setStrategy(String(event.target.value))}>
                  {calculators.map((item) => <MenuItem key={item.slug} value={item.slug}>{item.label}</MenuItem>)}
                </Select>
              </FormControl>
              <Typography variant="body2" color="text.secondary">{selected?.description}</Typography>
              <TextField label="Inputs (JSON)" value={inputs} onChange={(event) => setInputs(event.target.value)} multiline minRows={8} fullWidth inputProps={{ spellCheck: false }} />
              <Button variant="contained" onClick={run} disabled={running || !strategy}>{running ? "Running..." : "Run calculator"}</Button>
            </Stack>
          </CardContent>
        </Card>
        {result !== null && <Card variant="outlined"><CardContent><Typography variant="h6" gutterBottom>Result</Typography><Box component="pre" sx={{ m: 0, overflow: "auto", whiteSpace: "pre-wrap", fontFamily: "monospace" }}>{JSON.stringify(result, null, 2)}</Box></CardContent></Card>}
      </Stack>
    </Box>
  );
}
