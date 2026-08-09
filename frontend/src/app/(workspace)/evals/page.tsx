"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import { useSearchParams } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import EvalCaseResultDrawer from "@/components/evals/EvalCaseResultDrawer";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import {
  fetchEvalSuites,
  runAllEvals,
  runEvalSuite,
  runReleaseGate,
  type EvalSuiteResult,
  type EvalTaskResult,
  type ReleaseGate,
} from "@/lib/evals-harness-api";
import {
  fetchBenchmarkSuites,
  runBenchmarkAll,
  runBenchmarkRegression,
  runBenchmarkSuite,
} from "@/lib/evals-benchmarks-api";

const relatedSurfaces = [
  {
    title: "LLM usage and cost",
    description: "Operational spend, token volume, and model breakdown for your account.",
    href: "/usage",
  },
  {
    title: "TypeScript SDK evals",
    description: "Define local eval suites and trace aware workflow runs.",
    href: "/developer/sdk",
  },
  {
    title: "RAG pipeline evals",
    description: "Precision, faithfulness, and latency reports per pipeline run.",
    href: "/rag-pipeline",
  },
  {
    title: "Agent app eval suites",
    description: "YAML eval cases bundled with portable agent apps.",
    href: "/agent-apps",
  },
];

export default function EvalsPage() {
  const searchParams = useSearchParams();
  const { data } = useSWR("eval-suites", fetchEvalSuites);
  const benchmarks = useSWR("eval-benchmark-suites", fetchBenchmarkSuites);
  const [results, setResults] = React.useState<EvalSuiteResult[]>([]);
  const [gate, setGate] = React.useState<ReleaseGate | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [running, setRunning] = React.useState(false);
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [selectedTask, setSelectedTask] = React.useState<EvalTaskResult | null>(null);
  const [selectedSuite, setSelectedSuite] = React.useState<string | undefined>();
  const [benchResult, setBenchResult] = React.useState<unknown>(null);

  const suites = data?.suites ?? [];

  const openFailedCase = (suiteName: string, task: EvalTaskResult) => {
    setSelectedSuite(suiteName);
    setSelectedTask(task);
    setDrawerOpen(true);
  };

  React.useEffect(() => {
    const trace = searchParams.get("trace");
    if (!trace) return;
    setSelectedTask({
      task_id: "trace",
      passed: false,
      trace_id: trace,
      reason: "Opened from trace permalink",
    });
    setDrawerOpen(true);
  }, [searchParams]);

  const handleRunAll = async () => {
    setRunning(true);
    setError(null);
    try {
      const payload = await runAllEvals();
      setResults(payload.suites);
      setGate(payload.release_gate);
      setMessage(payload.release_gate.passed ? "Release gate passed" : "Release gate failed");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setRunning(false);
    }
  };

  const handleRunSuite = async (suiteName: string) => {
    setRunning(true);
    setError(null);
    try {
      const result = await runEvalSuite(suiteName);
      setResults((prev) => {
        const next = prev.filter((row) => row.suite !== suiteName);
        return [...next, result];
      });
      setMessage(`Suite ${suiteName}: ${(result.pass_rate * 100).toFixed(0)}% pass rate`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suite run failed");
    } finally {
      setRunning(false);
    }
  };

  const handleReleaseGate = async () => {
    setRunning(true);
    setError(null);
    try {
      const payload = await runReleaseGate(0.9);
      setGate(payload.release_gate);
      setMessage(payload.release_gate.passed ? "Release gate passed" : "Release gate failed");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Release gate failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Evals"
        description="Repeatable golden-task benchmarks, provider comparison, and release gate reports."
      />
      {message ? <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert> : null}
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
        <Button variant="contained" disabled={running} onClick={() => void handleRunAll()}>
          Run all suites
        </Button>
        <Button variant="outlined" disabled={running} onClick={() => void handleReleaseGate()}>
          Release gate
        </Button>
      </Box>
      {gate ? (
        <Alert severity={gate.passed ? "success" : "warning"} sx={{ mb: 2 }}>
          Release gate: {gate.passed ? "PASS" : "FAIL"} ({(gate.pass_rate * 100).toFixed(1)}% pass rate)
        </Alert>
      ) : null}
      <Typography variant="h6" sx={{ mb: 1 }}>
        Golden task suites ({suites.length})
      </Typography>
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { md: "1fr 1fr" }, mb: 4 }}>
        {suites.map((suite) => {
          const result = results.find((row) => row.suite === suite);
          const failedTasks = result?.tasks.filter((task) => !task.passed) ?? [];
          return (
            <Card key={suite} variant="outlined">
              <CardContent>
                <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1, mb: 1 }}>
                  <Typography variant="h6">{suite}</Typography>
                  {result ? <Chip size="small" label={`${(result.pass_rate * 100).toFixed(0)}%`} /> : null}
                </Box>
                <Button size="small" disabled={running} onClick={() => void handleRunSuite(suite)}>
                  Run suite
                </Button>
                {failedTasks.length > 0 ? (
                  <Box sx={{ mt: 2, display: "grid", gap: 0.5 }}>
                    <Typography variant="caption" color="text.secondary">
                      Failed cases
                    </Typography>
                    {failedTasks.map((task) => (
                      <Button
                        key={task.task_id}
                        size="small"
                        color="warning"
                        variant="outlined"
                        onClick={() => openFailedCase(suite, task)}
                        sx={{ justifyContent: "flex-start", textTransform: "none" }}
                      >
                        {task.task_id}
                        {task.reason ? ` · ${task.reason}` : ""}
                      </Button>
                    ))}
                  </Box>
                ) : null}
              </CardContent>
            </Card>
          );
        })}
      </Box>
      <EvalCaseResultDrawer
        open={drawerOpen}
        task={selectedTask}
        suiteName={selectedSuite}
        onClose={() => setDrawerOpen(false)}
      />
      <Typography variant="h6" sx={{ mb: 1 }}>
        Benchmark suites ({(benchmarks.data?.suites || []).length})
      </Typography>
      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
        <Button
          variant="outlined"
          disabled={running}
          onClick={() => {
            void (async () => {
              setRunning(true);
              setError(null);
              try {
                setBenchResult(await runBenchmarkAll());
                setMessage("Benchmark run finished");
              } catch (err) {
                setError(err instanceof Error ? err.message : "Benchmark run failed");
              } finally {
                setRunning(false);
              }
            })();
          }}
        >
          Run all benchmarks
        </Button>
        <Button
          variant="outlined"
          disabled={running}
          onClick={() => {
            void (async () => {
              setRunning(true);
              setError(null);
              try {
                setBenchResult(await runBenchmarkRegression());
                setMessage("Regression check finished");
              } catch (err) {
                setError(err instanceof Error ? err.message : "Regression failed");
              } finally {
                setRunning(false);
              }
            })();
          }}
        >
          Regression vs baseline
        </Button>
      </Box>
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { md: "1fr 1fr" }, mb: 4 }}>
        {(benchmarks.data?.suites || []).map((suite) => (
          <Card key={suite} variant="outlined">
            <CardContent>
              <Typography variant="h6">{suite}</Typography>
              <Button
                size="small"
                disabled={running}
                onClick={() => {
                  void (async () => {
                    setRunning(true);
                    setError(null);
                    try {
                      setBenchResult(await runBenchmarkSuite(suite));
                      setMessage(`Benchmark suite ${suite} finished`);
                    } catch (err) {
                      setError(err instanceof Error ? err.message : "Suite failed");
                    } finally {
                      setRunning(false);
                    }
                  })();
                }}
              >
                Run benchmark
              </Button>
            </CardContent>
          </Card>
        ))}
      </Box>
      {benchResult ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          <StructuredDataView value={benchResult} />
        </Alert>
      ) : null}
      <Typography variant="h6" sx={{ mb: 1 }}>
        Related eval surfaces
      </Typography>
      <Box sx={{ display: "grid", gap: 2 }}>
        {relatedSurfaces.map((item) => (
          <Card key={item.title} variant="outlined">
            <CardContent>
              <Typography variant="h6">{item.title}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                {item.description}
              </Typography>
              <Button component="a" href={item.href} size="small" sx={{ mt: 2 }}>
                Open
              </Button>
            </CardContent>
          </Card>
        ))}
      </Box>
    </Box>
  );
}
