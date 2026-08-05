"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Collapse from "@mui/material/Collapse";
import Divider from "@mui/material/Divider";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import UploadFileOutlinedIcon from "@mui/icons-material/UploadFileOutlined";
import { useTheme } from "@mui/material/styles";
import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import { SkeletonChart, SkeletonTable } from "@/components/ui/loading";
import {
  createAnalyticsSession,
  deleteAnalyticsDataset,
  downloadJamoviPackage,
  fetchAnalyticsDataset,
  fetchAnalyticsSession,
  fetchAnalyticsSessions,
  listAnalyticsDatasets,
  parseAnalyticsFile,
  parseCsvToRows,
  renameAnalyticsSession,
  runAnalyticsCode,
  saveAnalyticsDataset,
} from "@/lib/analytics-api";
import {
  fetchResearchProjects,
  sendAnalyticsToResearchProject,
  type ResearchProject,
} from "@/lib/research-workspace-api";

const ACCEPTED_FILE_TYPES =
  ".csv,.tsv,.txt,.md,.markdown,.json,.jsonl,.ndjson,.xlsx,.xlsm,.pdf,.docx,.parquet,.sav";

const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

// ---- Types ----

type AnalysisType = "summary" | "averages" | "totals" | "top5" | "compare" | "trend";

type AnalysisResult = {
  type: "bar" | "line" | "error";
  answer: string;
  chart_data?: Array<{ x: string; y: number }>;
  chart_title?: string;
  stats?: Record<string, number>;
};

// ---- Suggestion chips ----

const SUGGESTIONS: Array<{ label: string; type: AnalysisType }> = [
  { label: "What are the averages?", type: "averages" },
  { label: "Show me totals", type: "totals" },
  { label: "Which is the highest?", type: "top5" },
  { label: "Compare groups", type: "compare" },
  { label: "Show a trend", type: "trend" },
];

const EXAMPLE_DATA = `name,score,group
Alice,85,A
Bob,92,B
Carol,78,A
David,95,B
Eve,88,A
Frank,76,B`;

// ---- Helpers ----

function normalizeData(raw: string): string {
  const lines = raw.trim().split(/\r?\n/).filter((l) => l.trim());
  if (lines.length === 0) return "";
  const normalized = lines.map((line) => line.replace(/\t/g, ",").replace(/;/g, ","));
  // If first row is all-numeric, add a generic header
  const firstCells = normalized[0].split(",").map((c) => c.trim());
  const firstIsAllNumeric = firstCells.every((c) => c !== "" && !isNaN(Number(c)));
  if (firstIsAllNumeric) {
    const header =
      firstCells.length === 1
        ? "value"
        : firstCells.map((_, i) => `col${i + 1}`).join(",");
    return [header, ...normalized].join("\n");
  }
  return normalized.join("\n");
}

function detectAnalysis(question: string): AnalysisType {
  const q = question.toLowerCase();
  if (/average|mean|typical|avg|median/.test(q)) return "averages";
  if (/total|sum|add up|cumulative|aggregate/.test(q)) return "totals";
  if (/top|highest|most|best|biggest|largest|max|rank/.test(q)) return "top5";
  if (/compare|group|differ|between|vs\.?\s|versus|breakdown|by\s+\w+/.test(q)) return "compare";
  if (/trend|over time|change|grow|increase|decrease|progress|time series|monthly|weekly/.test(q)) {
    return "trend";
  }
  if (/count|how many|frequency|distribution/.test(q)) return "summary";
  if (/correlate|correlation|relationship|scatter/.test(q)) return "compare";
  return "summary";
}

function buildPython(type: AnalysisType, data: string): string {
  // Escape triple-quotes and backslashes so the data embeds safely in a Python triple-quoted string
  const escaped = data.replace(/\\/g, "\\\\").replace(/"""/g, '\\"\\"\\"');

  const base = `import csv, io, json
raw = """${escaped}"""
reader = csv.DictReader(io.StringIO(raw.strip()))
rows = list(reader)
cols = list(rows[0].keys()) if rows else []
def _f(v):
    try: float(v); return True
    except: return False
num_cols = [c for c in cols if sum(1 for r in rows if _f(r.get(c,""))) > len(rows)*0.4]
text_cols = [c for c in cols if c not in num_cols]
`;

  const bodies: Record<AnalysisType, string> = {
    summary: `
if not rows:
    print(json.dumps({"type":"error","answer":"No data found. Paste your data above."}))
elif num_cols:
    col = num_cols[0]
    vals = [float(r[col]) for r in rows if _f(r.get(col,""))]
    avg = round(sum(vals)/len(vals),2)
    lbl = text_cols[0] if text_cols else None
    cd = [{"x":r.get(lbl,str(i+1)),"y":float(r[col])} for i,r in enumerate(rows) if _f(r.get(col,""))]
    stats = {"average":avg,"min":round(min(vals),2),"max":round(max(vals),2),"count":len(vals)}
    ans = f"Your data has {len(rows)} rows. Average {col}: {avg}. Range: {stats['min']} to {stats['max']}."
    print(json.dumps({"type":"bar","answer":ans,"chart_data":cd[:20],"chart_title":col,"stats":stats}))
else:
    col = text_cols[0] if text_cols else cols[0]
    counts = {}
    for r in rows: counts[r.get(col,"")] = counts.get(r.get(col,""),0)+1
    cd = [{"x":k,"y":v} for k,v in sorted(counts.items(),key=lambda x:-x[1])[:10]]
    print(json.dumps({"type":"bar","answer":f"Your data has {len(rows)} rows with {len(counts)} unique {col} values.","chart_data":cd,"chart_title":col}))
`,
    averages: `
if not num_cols:
    print(json.dumps({"type":"error","answer":"No numeric columns found. Make sure your data includes numbers."}))
elif text_cols:
    gc,vc = text_cols[0],num_cols[0]
    groups = {}
    for r in rows:
        g = r.get(gc,"")
        if _f(r.get(vc,"")): groups.setdefault(g,[]).append(float(r[vc]))
    avgs = {g:round(sum(v)/len(v),2) for g,v in groups.items()}
    best = max(avgs,key=avgs.get) if avgs else ""
    cd = [{"x":g,"y":v} for g,v in sorted(avgs.items(),key=lambda x:-x[1])]
    preview = ", ".join(f"{g} = {v}" for g,v in list(avgs.items())[:4])
    ans = f"Average {vc} by {gc}: {preview}." + (f" Highest: {best} ({avgs[best]})." if best else "")
    print(json.dumps({"type":"bar","answer":ans,"chart_data":cd,"chart_title":f"Average {vc} by {gc}"}))
else:
    cd = [{"x":c,"y":round(sum(float(r[c]) for r in rows if _f(r.get(c,"")))/max(1,sum(1 for r in rows if _f(r.get(c,"")))),2)} for c in num_cols]
    ans = "Column averages: " + ", ".join(f"{d['x']} = {d['y']}" for d in cd[:5]) + "."
    print(json.dumps({"type":"bar","answer":ans,"chart_data":cd,"chart_title":"Column Averages"}))
`,
    totals: `
if not num_cols:
    print(json.dumps({"type":"error","answer":"No numeric columns found."}))
else:
    cd = [{"x":c,"y":round(sum(float(r[c]) for r in rows if _f(r.get(c,""))),2)} for c in num_cols]
    ans = "Totals: " + ", ".join(f"{d['x']} = {d['y']}" for d in cd[:5]) + "."
    print(json.dumps({"type":"bar","answer":ans,"chart_data":cd,"chart_title":"Column Totals"}))
`,
    top5: `
if not num_cols:
    print(json.dumps({"type":"error","answer":"No numeric columns found."}))
else:
    vc = num_cols[0]
    lc = text_cols[0] if text_cols else None
    pairs = [(r.get(lc,str(i+1)) if lc else str(i+1),float(r[vc])) for i,r in enumerate(rows) if _f(r.get(vc,""))]
    pairs.sort(key=lambda x:-x[1])
    top = pairs[:5]
    cd = [{"x":p[0],"y":p[1]} for p in top]
    ans = f"Top 5 by {vc}: " + ", ".join(f"{p[0]} ({p[1]})" for p in top[:3]) + ("." if len(top) < 3 else f". Highest: {top[0][0]} with {top[0][1]}." if top else ".")
    print(json.dumps({"type":"bar","answer":ans,"chart_data":cd,"chart_title":f"Top 5 by {vc}"}))
`,
    compare: `
if not text_cols or not num_cols:
    print(json.dumps({"type":"error","answer":"Need a text column (for group names) and a numeric column to compare."}))
else:
    gc,vc = text_cols[0],num_cols[0]
    groups = {}
    for r in rows:
        g = r.get(gc,"")
        if _f(r.get(vc,"")): groups.setdefault(g,[]).append(float(r[vc]))
    res = {g:round(sum(v)/len(v),2) for g,v in groups.items()}
    cd = [{"x":g,"y":v} for g,v in sorted(res.items(),key=lambda x:-x[1])]
    if len(res) >= 2:
        mx,mn = max(res,key=res.get),min(res,key=res.get)
        diff = round(res[mx]-res[mn],2)
        ans = f"{mx} has the highest average {vc} ({res[mx]}), {mn} has the lowest ({res[mn]}). Difference: {diff}."
    else:
        ans = "Only one group found. Your data needs a column with different group labels to compare."
    print(json.dumps({"type":"bar","answer":ans,"chart_data":cd,"chart_title":f"{vc} by {gc}"}))
`,
    trend: `
if not num_cols:
    print(json.dumps({"type":"error","answer":"No numeric columns found."}))
else:
    vc = num_cols[0]
    lc = cols[0] if cols[0] != vc else (text_cols[0] if text_cols else None)
    pairs = [(r.get(lc,str(i+1)) if lc else str(i+1),float(r[vc])) for i,r in enumerate(rows) if _f(r.get(vc,""))]
    cd = [{"x":p[0],"y":p[1]} for p in pairs[:30]]
    if len(pairs) >= 2:
        chg = round(pairs[-1][1]-pairs[0][1],2)
        pct = round(chg/pairs[0][1]*100,1) if pairs[0][1] != 0 else 0
        dirn = "increased" if chg > 0 else ("decreased" if chg < 0 else "stayed flat")
        ans = f"{vc} {dirn} from {pairs[0][1]} to {pairs[-1][1]} over {len(pairs)} data points (change: {chg}, {pct:+}%)."
    else:
        ans = "Not enough data points to show a trend. Need at least 2 rows."
    print(json.dumps({"type":"line","answer":ans,"chart_data":cd,"chart_title":f"{vc} over time"}))
`,
  };

  return base + bodies[type];
}

// ---- Page ----

export default function AnalyticsPanel() {
  const theme = useTheme();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [data, setData] = React.useState("");
  const [question, setQuestion] = React.useState("");
  const [sessionId, setSessionId] = React.useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = React.useState<AnalysisResult | null>(null);
  const [generatedCode, setGeneratedCode] = React.useState<string | null>(null);
  const [codeVisible, setCodeVisible] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [uploadBusy, setUploadBusy] = React.useState(false);
  const [uploadInfo, setUploadInfo] = React.useState<string | null>(null);
  const [dragActive, setDragActive] = React.useState(false);
  const [jamoviBusy, setJamoviBusy] = React.useState(false);
  const [handoffBusy, setHandoffBusy] = React.useState(false);
  const [handoffProjectId, setHandoffProjectId] = React.useState("");
  const [sessionTitle, setSessionTitle] = React.useState("Untitled session");
  const [datasetName, setDatasetName] = React.useState("");
  const [codeHistory, setCodeHistory] = React.useState<string[]>([]);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const { data: sessionsPayload, mutate: mutateSessions } = useSWR("analytics-sessions", fetchAnalyticsSessions);
  const { data: datasetsPayload, mutate: mutateDatasets } = useSWR("analytics-datasets", listAnalyticsDatasets);
  const { data: projectsPayload } = useSWR("research-projects-handoff", fetchResearchProjects);
  const sessions = sessionsPayload?.sessions ?? [];
  const datasets = datasetsPayload?.datasets ?? [];
  const projects: ResearchProject[] = projectsPayload?.items ?? [];

  React.useEffect(() => {
    const fromQuery = searchParams.get("session");
    if (!fromQuery || fromQuery === sessionId) {
      return;
    }
    let active = true;
    void fetchAnalyticsSession(fromQuery)
      .then((session) => {
        if (!active) return;
        setSessionId(session.session_id);
        setSessionTitle(session.title || "Untitled session");
        if (session.code_history?.length) {
          setGeneratedCode(session.code_history[session.code_history.length - 1]);
          setCodeHistory(session.code_history);
        }
        setUploadInfo(`Loaded session ${session.title || session.session_id.slice(0, 8)} from link.`);
      })
      .catch(() => {
        if (active) {
          setError("Could not load analytics session from link.");
        }
      });
    return () => {
      active = false;
    };
  }, [searchParams, sessionId]);

  const selectSession = React.useCallback(
    (id: string) => {
      setSessionId(id);
      const params = new URLSearchParams(searchParams.toString());
      params.set("session", id);
      params.set("tab", "analytics");
      router.replace(`/data?${params.toString()}`);
      void fetchAnalyticsSession(id)
        .then((session) => {
          setSessionTitle(session.title || "Untitled session");
          if (session.code_history?.length) {
            setGeneratedCode(session.code_history[session.code_history.length - 1]);
            setCodeHistory(session.code_history);
          }
        })
        .catch(() => setError("Could not load selected session."));
    },
    [router, searchParams],
  );

  const handleFileUpload = React.useCallback(async (file: File) => {
    setUploadBusy(true);
    setError(null);
    setUploadInfo(null);
    try {
      const result = await parseAnalyticsFile(file);
      setData(result.data);
      setDatasetName(result.filename.replace(/\.[^.]+$/, "") || "Dataset");
      const title = result.filename.replace(/\.[^.]+$/, "") || "Untitled session";
      setSessionTitle(title);
      if (!sessionId) {
        const created = await createAnalyticsSession(title);
        setSessionId(created.session_id);
        void mutateSessions();
        const params = new URLSearchParams(searchParams.toString());
        params.set("session", created.session_id);
        params.set("tab", "analytics");
        router.replace(`/data?${params.toString()}`);
      } else {
        await renameAnalyticsSession(sessionId, title).catch(() => null);
        void mutateSessions();
      }
      const rows =
        result.row_count > 0
          ? `${result.row_count} row${result.row_count === 1 ? "" : "s"}`
          : "data";
      setUploadInfo(
        `Imported ${result.filename} (${result.source_type}, ${rows}).` +
          (result.message ? ` ${result.message}` : ""),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not import file.");
    } finally {
      setUploadBusy(false);
      setDragActive(false);
    }
  }, []);

  const onFileInputChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (file) void handleFileUpload(file);
      event.target.value = "";
    },
    [handleFileUpload],
  );

  const onDrop = React.useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      setDragActive(false);
      const file = event.dataTransfer.files?.[0];
      if (file) void handleFileUpload(file);
    },
    [handleFileUpload],
  );

  const handleJamoviDownload = React.useCallback(async () => {
    const normalized = normalizeData(data);
    let rows: Array<Record<string, unknown>> = [];
    try {
      rows = parseCsvToRows(normalized);
    } catch (err) {
      setError(err instanceof Error ? err.message : "CSV parse failed.");
      return;
    }
    if (!rows.length) {
      setError("Add data with a header row before downloading for jamovi.");
      return;
    }
    setJamoviBusy(true);
    setError(null);
    try {
      await downloadJamoviPackage(rows, "analytics-export");
      setUploadInfo("jamovi package downloaded. Open the zip in jamovi on your computer.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "jamovi download failed");
    } finally {
      setJamoviBusy(false);
    }
  }, [data]);

  const getSession = React.useCallback(async () => {
    if (sessionId) return sessionId;
    const s = await createAnalyticsSession(sessionTitle);
    setSessionId(s.session_id);
    setSessionTitle(s.title || sessionTitle);
    void mutateSessions();
    const params = new URLSearchParams(searchParams.toString());
    params.set("session", s.session_id);
    params.set("tab", "analytics");
    router.replace(`/data?${params.toString()}`);
    return s.session_id;
  }, [sessionId, sessionTitle, mutateSessions, router, searchParams]);

  const analyze = React.useCallback(
    async (overrideType?: AnalysisType) => {
      const normalized = normalizeData(data);
      if (!normalized) {
        setError("Paste some data above before analyzing.");
        return;
      }
      const type = overrideType ?? detectAnalysis(question);
      const code = buildPython(type, normalized);
      setGeneratedCode(code);
      setCodeHistory((prev) => [...prev, code]);
      setBusy(true);
      setError(null);
      setAnalysisResult(null);

      try {
        const id = await getSession();
        const run = await runAnalyticsCode(id, code, true);

        let parsed: AnalysisResult | null = null;
        if (run.stdout) {
          try {
            parsed = JSON.parse(run.stdout.trim()) as AnalysisResult;
          } catch {
            parsed = { type: "bar", answer: run.stdout.trim() };
          }
        }
        if (!parsed) {
          parsed = {
            type: "error",
            answer: run.stderr || "No output returned. Try a different question or check your data format.",
          };
        }
        setAnalysisResult(parsed);
        void mutateSessions();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Analysis failed. Please try again.");
      } finally {
        setBusy(false);
      }
    },
    [data, question, getSession, mutateSessions],
  );

  const handleResearchHandoff = React.useCallback(async () => {
    if (!handoffProjectId) {
      setError("Choose a research project before sending results.");
      return;
    }
    if (!analysisResult || analysisResult.type === "error") {
      setError("Run an analysis before sending to research.");
      return;
    }
    setHandoffBusy(true);
    setError(null);
    try {
      const id = sessionId || (await getSession());
      await sendAnalyticsToResearchProject(handoffProjectId, {
        title: question.trim() || "Analytics workspace handoff",
        summary: analysisResult.answer,
        chart_export: analysisResult.chart_data,
        analytics_session_id: id,
      });
      setUploadInfo("Analysis sent to research project.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Research handoff failed.");
    } finally {
      setHandoffBusy(false);
    }
  }, [analysisResult, getSession, handoffProjectId, question, sessionId]);

  const handleChip = (type: AnalysisType, label: string) => {
    setQuestion(label);
    void analyze(type);
  };

  const chartData = analysisResult?.chart_data ?? [];
  const chartType = analysisResult?.type === "line" ? "line" : "bar";

  return (
    <Box>

      {uploadInfo ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setUploadInfo(null)}>
          {uploadInfo}
        </Alert>
      ) : null}

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "240px 1fr" }, gap: 2 }}>
        <Card variant="outlined" sx={{ alignSelf: "start" }}>
          <CardContent>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Recent sessions
            </Typography>
            {sessionId ? (
              <TextField
                size="small"
                fullWidth
                label="Session title"
                value={sessionTitle}
                onChange={(e) => setSessionTitle(e.target.value)}
                onBlur={() => {
                  if (!sessionId) return;
                  void renameAnalyticsSession(sessionId, sessionTitle)
                    .then(() => mutateSessions())
                    .catch(() => null);
                }}
                sx={{ mb: 1.5 }}
              />
            ) : null}
            {sessions.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                Sessions appear after your first analysis run.
              </Typography>
            ) : (
              <Box sx={{ display: "grid", gap: 0.5 }}>
                {sessions.slice(0, 12).map((session) => (
                  <Button
                    key={session.session_id}
                    size="small"
                    variant={session.session_id === sessionId ? "contained" : "text"}
                    onClick={() => selectSession(session.session_id)}
                    sx={{ justifyContent: "flex-start", textTransform: "none" }}
                  >
                    <Box sx={{ textAlign: "left" }}>
                      <Typography variant="body2">
                        {session.title || session.session_id.slice(0, 8)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {session.code_runs ?? session.code_history?.length ?? 0} runs
                      </Typography>
                    </Box>
                  </Button>
                ))}
              </Box>
            )}

            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Dataset library
            </Typography>
            <TextField
              size="small"
              fullWidth
              label="Dataset name"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              sx={{ mb: 1 }}
            />
            <Button
              size="small"
              variant="outlined"
              fullWidth
              sx={{ mb: 1 }}
              disabled={!data.trim()}
              onClick={() => {
                void saveAnalyticsDataset({
                  name: datasetName || sessionTitle || "Dataset",
                  data,
                  source_filename: datasetName || undefined,
                })
                  .then(() => {
                    void mutateDatasets();
                    setUploadInfo("Dataset saved.");
                  })
                  .catch((err) => setError(err instanceof Error ? err.message : "Save failed"));
              }}
            >
              Save dataset
            </Button>
            {datasets.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                Saved datasets appear here.
              </Typography>
            ) : (
              <Box sx={{ display: "grid", gap: 0.5 }}>
                {datasets.slice(0, 12).map((dataset) => (
                  <Stack key={dataset.dataset_id} direction="row" spacing={0.5} alignItems="center">
                    <Button
                      size="small"
                      sx={{ flex: 1, justifyContent: "flex-start", textTransform: "none" }}
                      onClick={() => {
                        void fetchAnalyticsDataset(dataset.dataset_id).then((full) => {
                          setData(full.data || "");
                          setDatasetName(full.name);
                          setUploadInfo(`Opened dataset ${full.name}.`);
                        });
                      }}
                    >
                      {dataset.name}
                    </Button>
                    <Button
                      size="small"
                      color="warning"
                      onClick={() => {
                        void deleteAnalyticsDataset(dataset.dataset_id).then(() => mutateDatasets());
                      }}
                    >
                      Del
                    </Button>
                  </Stack>
                ))}
              </Box>
            )}

            {codeHistory.length > 0 ? (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle1" sx={{ mb: 1 }}>
                  Run history
                </Typography>
                <Box sx={{ display: "grid", gap: 0.5, maxHeight: 180, overflow: "auto" }}>
                  {codeHistory
                    .slice()
                    .reverse()
                    .slice(0, 12)
                    .map((code, index) => (
                      <Button
                        key={`${index}-${code.slice(0, 12)}`}
                        size="small"
                        variant="text"
                        sx={{ justifyContent: "flex-start", textTransform: "none" }}
                        onClick={() => {
                          setGeneratedCode(code);
                          setCodeVisible(true);
                          void (async () => {
                            setBusy(true);
                            try {
                              const id = await getSession();
                              const run = await runAnalyticsCode(id, code, true);
                              let parsed: AnalysisResult | null = null;
                              if (run.stdout) {
                                try {
                                  parsed = JSON.parse(run.stdout.trim()) as AnalysisResult;
                                } catch {
                                  parsed = { type: "bar", answer: run.stdout.trim() };
                                }
                              }
                              setAnalysisResult(
                                parsed || {
                                  type: "error",
                                  answer: run.stderr || "No output returned.",
                                },
                              );
                            } catch (err) {
                              setError(err instanceof Error ? err.message : "Re-run failed");
                            } finally {
                              setBusy(false);
                            }
                          })();
                        }}
                      >
                        Re-run #{codeHistory.length - index}
                      </Button>
                    ))}
                </Box>
              </>
            ) : null}
          </CardContent>
        </Card>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {/* Data input */}
        <Card variant="outlined">
          <CardContent>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
              <Typography variant="subtitle1">Your data</Typography>
              <Box sx={{ display: "flex", gap: 1.5, alignItems: "center" }}>
                <Link
                  component="button"
                  variant="body2"
                  onClick={() => fileInputRef.current?.click()}
                  underline="hover"
                  sx={{ cursor: "pointer" }}
                  disabled={uploadBusy}
                >
                  Upload file
                </Link>
                <Link
                  component="button"
                  variant="body2"
                  onClick={() => setData(EXAMPLE_DATA)}
                  underline="hover"
                  sx={{ cursor: "pointer" }}
                >
                  Load example
                </Link>
              </Box>
            </Box>

            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_FILE_TYPES}
              hidden
              onChange={onFileInputChange}
            />

            <Box
              onDragOver={(event) => {
                event.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={onDrop}
              onClick={() => !uploadBusy && fileInputRef.current?.click()}
              sx={{
                mb: 1.5,
                p: 2,
                border: "1px dashed",
                borderColor: dragActive ? "primary.main" : "divider",
                borderRadius: 1,
                bgcolor: dragActive ? "action.hover" : "background.default",
                cursor: uploadBusy ? "default" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 1.5,
                minHeight: 72,
              }}
            >
              {uploadBusy ? (
                <CircularProgress size={22} />
              ) : (
                <UploadFileOutlinedIcon color="action" fontSize="small" />
              )}
              <Box>
                <Typography variant="body2">
                  {uploadBusy ? "Importing file..." : "Drop a file here or click to upload"}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  CSV, TSV, Excel, SPSS (.sav), JSON, PDF, Word, Markdown, Parquet (max 10 MB)
                </Typography>
              </Box>
            </Box>

            <TextField
              value={data}
              onChange={(e) => setData(e.target.value)}
              multiline
              minRows={5}
              maxRows={12}
              fullWidth
              placeholder={`Paste from a spreadsheet or upload a file above.\nFirst row should be column names.\n\nExample:\nname,score,group\nAlice,85,A\nBob,92,B`}
              inputProps={{ style: { fontFamily: "monospace", fontSize: "0.83rem" } }}
            />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
              Upload CSV, Excel, SPSS (.sav), or JSON for best results. PDF and Word are converted to text when
              possible.
            </Typography>
            <Box sx={{ mt: 1.5, display: "flex", gap: 1, flexWrap: "wrap" }}>
              <Button
                size="small"
                variant="outlined"
                onClick={() => void handleJamoviDownload()}
                disabled={jamoviBusy || !data.trim()}
              >
                {jamoviBusy ? "Preparing..." : "Download for jamovi"}
              </Button>
            </Box>
          </CardContent>
        </Card>

        {/* Question */}
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" sx={{ mb: 1.5 }}>
              What would you like to know?
            </Typography>
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 1.5 }}>
              {SUGGESTIONS.map((s) => (
                <Chip
                  key={s.type}
                  label={s.label}
                  variant={question === s.label ? "filled" : "outlined"}
                  color={question === s.label ? "primary" : "default"}
                  onClick={() => handleChip(s.type, s.label)}
                  disabled={busy}
                  size="small"
                />
              ))}
            </Box>
            <Box sx={{ display: "flex", gap: 1 }}>
              <TextField
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void analyze();
                }}
                placeholder="Or type your own question..."
                size="small"
                fullWidth
              />
              <Button
                variant="contained"
                onClick={() => void analyze()}
                disabled={busy || !data.trim()}
                sx={{ whiteSpace: "nowrap", flexShrink: 0 }}
              >
                {busy ? "Analyzing..." : "Analyze"}
              </Button>
            </Box>
          </CardContent>
        </Card>

        {/* Results */}
        {busy ? (
          <Card variant="outlined">
            <CardContent>
              <SkeletonChart height={260} />
              <Box sx={{ mt: 2 }}>
                <SkeletonTable rows={3} columns={3} />
              </Box>
            </CardContent>
          </Card>
        ) : analysisResult ? (
          <Card variant="outlined">
            <CardContent>
              {analysisResult.type === "error" ? (
                <Alert severity="warning">{analysisResult.answer}</Alert>
              ) : (
                <>
                  <Typography variant="body1" sx={{ fontWeight: 500, mb: analysisResult.stats ? 2 : 0 }}>
                    {analysisResult.answer}
                  </Typography>

                  {analysisResult.stats ? (
                    <Box sx={{ display: "flex", gap: 3, flexWrap: "wrap", mb: 2 }}>
                      {Object.entries(analysisResult.stats).map(([k, v]) => (
                        <Box key={k} sx={{ textAlign: "center" }}>
                          <Typography variant="h6" color="primary.main" sx={{ lineHeight: 1.2 }}>
                            {v}
                          </Typography>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ textTransform: "capitalize" }}
                          >
                            {k}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  ) : null}

                  {chartData.length > 0 ? (
                    <Chart
                      type={chartType}
                      height={260}
                      series={[
                        {
                          name: analysisResult.chart_title ?? "Value",
                          data: chartData.map((d) => d.y),
                        },
                      ]}
                      options={{
                        chart: {
                          toolbar: {
                            show: true,
                            export: {
                              csv: { filename: "keprix-chart" },
                              svg: { filename: "keprix-chart" },
                              png: { filename: "keprix-chart" },
                            },
                          },
                          foreColor: theme.palette.text.secondary,
                          background: "transparent",
                        },
                        colors: [theme.palette.primary.main],
                        plotOptions:
                          chartType === "bar"
                            ? {
                                bar: {
                                  borderRadius: 4,
                                  horizontal: chartData.length > 7,
                                },
                              }
                            : {},
                        dataLabels: { enabled: false },
                        stroke: chartType === "line" ? { curve: "smooth", width: 2 } : undefined,
                        xaxis: { categories: chartData.map((d) => d.x) },
                        grid: { borderColor: theme.palette.divider },
                        tooltip: { theme: theme.palette.mode },
                      }}
                    />
                  ) : (
                    <Alert severity="info" sx={{ mt: 1 }}>
                      No chart points for this result. Try totals, averages, or top values.
                    </Alert>
                  )}

                  <Divider sx={{ my: 2 }} />
                  <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", alignItems: "center", mb: 2 }}>
                    <TextField
                      select
                      size="small"
                      label="Research project"
                      value={handoffProjectId}
                      onChange={(event) => setHandoffProjectId(event.target.value)}
                      SelectProps={{ native: true }}
                      sx={{ minWidth: 220 }}
                    >
                      <option value="">Select project</option>
                      {projects.map((project) => (
                        <option key={project.project_id} value={project.project_id}>
                          {project.title}
                        </option>
                      ))}
                    </TextField>
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={handoffBusy || !analysisResult}
                      onClick={() => void handleResearchHandoff()}
                    >
                      {handoffBusy ? "Sending..." : "Send to research project"}
                    </Button>
                  </Box>
                  <Link
                    component="button"
                    variant="body2"
                    color="text.secondary"
                    onClick={() => setCodeVisible((v) => !v)}
                    underline="hover"
                    sx={{ cursor: "pointer" }}
                  >
                    {codeVisible ? "Hide code" : "Show how this was calculated"}
                  </Link>
                  <Collapse in={codeVisible}>
                    <Box
                      component="pre"
                      sx={{
                        mt: 1.5,
                        p: 1.5,
                        bgcolor: "background.default",
                        borderRadius: 1,
                        fontSize: "0.75rem",
                        overflowX: "auto",
                        border: "1px solid",
                        borderColor: "divider",
                        maxHeight: 320,
                      }}
                    >
                      {generatedCode}
                    </Box>
                  </Collapse>
                </>
              )}
            </CardContent>
          </Card>
        ) : null}
        </Box>
      </Box>
    </Box>
  );
}
