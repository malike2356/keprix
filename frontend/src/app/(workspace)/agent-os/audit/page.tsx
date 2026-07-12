"use client";

import AddIcon from "@mui/icons-material/Add";
import DownloadIcon from "@mui/icons-material/Download";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SendIcon from "@mui/icons-material/Send";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Slider from "@mui/material/Slider";
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
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";

type AuditTask = {
  id: string;
  domain: string;
  description: string;
  frequency: string;
  desired_output: string;
  tools_hint?: string[];
  propose_skill: boolean;
  propose_automation: boolean;
};

type Audit = {
  audit_id: string;
  mode: string;
  status: string;
  tasks: AuditTask[];
  proposed_skills: Array<Record<string, unknown>>;
  proposed_automations?: Array<Record<string, unknown>>;
  session_ids_scanned?: string[];
  interview_transcript?: Array<{ role: string; content: string }>;
};

const domains = ["content", "sales", "ops", "research", "support", "custom"];
const frequencies = ["daily", "weekly", "ad_hoc"];

async function startAudit(mode: string, sessionCount = 10): Promise<Audit> {
  const response = await ceApi("/api/agent-os/audit/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, session_count: sessionCount }),
  });
  if (!response.ok) throw new Error("Failed to start audit");
  const payload = (await response.json()) as { audit: Audit };
  return payload.audit;
}

async function saveManualTasks(auditId: string, tasks: AuditTask[]): Promise<Audit> {
  const response = await ceApi(`/api/agent-os/audit/${auditId}/tasks`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tasks }),
  });
  if (!response.ok) throw new Error("Failed to save tasks");
  const payload = (await response.json()) as { audit: Audit };
  return payload.audit;
}

async function completeAudit(auditId: string): Promise<Audit> {
  const response = await ceApi(`/api/agent-os/audit/${auditId}/complete`, { method: "POST" });
  if (!response.ok) throw new Error("Failed to complete audit");
  const payload = (await response.json()) as { audit: Audit };
  return payload.audit;
}

async function exportProposals(auditId: string): Promise<number> {
  const response = await ceApi(`/api/agent-os/audit/${auditId}/export-to-proposals`, { method: "POST" });
  if (!response.ok) throw new Error("Failed to export proposals");
  const payload = (await response.json()) as { exported: number };
  return payload.exported;
}

function downloadAudit(audit: Audit) {
  const blob = new Blob([JSON.stringify(audit, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `workflow-audit-${audit.audit_id}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function WorkflowAuditPage() {
  const [tab, setTab] = React.useState(0);
  const [audit, setAudit] = React.useState<Audit | null>(null);
  const [description, setDescription] = React.useState("");
  const [desiredOutput, setDesiredOutput] = React.useState("");
  const [domain, setDomain] = React.useState("content");
  const [frequency, setFrequency] = React.useState("weekly");
  const [sessionCount, setSessionCount] = React.useState(10);
  const [interviewInput, setInterviewInput] = React.useState("");
  const [interviewLog, setInterviewLog] = React.useState<Array<{ role: string; content: string }>>([]);
  const [message, setMessage] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const runStart = async (mode: "manual" | "session_scan" | "interview") => {
    setBusy(true);
    setMessage(null);
    try {
      const next = await startAudit(mode, sessionCount);
      setAudit(next);
      setInterviewLog(next.interview_transcript || []);
      setMessage(mode === "session_scan" ? `Scanned ${next.session_ids_scanned?.length || 0} sessions.` : `Started ${mode} audit.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Start failed");
    } finally {
      setBusy(false);
    }
  };

  const persistTasks = async (tasks: AuditTask[]) => {
    if (!audit) return;
    const updated = await saveManualTasks(audit.audit_id, tasks);
    setAudit(updated);
  };

  const addManualTask = async () => {
    if (!audit || !description.trim()) return;
    await persistTasks([
      ...(audit.tasks || []),
      {
        id: crypto.randomUUID(),
        domain,
        description: description.trim(),
        frequency,
        desired_output: desiredOutput.trim(),
        tools_hint: [],
        propose_skill: true,
        propose_automation: frequency === "daily",
      },
    ]);
    setDescription("");
    setDesiredOutput("");
  };

  const updateTask = async (taskId: string, patch: Partial<AuditTask>) => {
    if (!audit) return;
    await persistTasks((audit.tasks || []).map((task) => (task.id === taskId ? { ...task, ...patch } : task)));
  };

  const finishAudit = async () => {
    if (!audit) return;
    setBusy(true);
    try {
      const completed = await completeAudit(audit.audit_id);
      setAudit(completed);
      setMessage(`Audit complete with ${completed.proposed_skills.length} skill proposal(s).`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Complete failed");
    } finally {
      setBusy(false);
    }
  };

  const exportAudit = async () => {
    if (!audit) return;
    setBusy(true);
    try {
      const exported = await exportProposals(audit.audit_id);
      setMessage(`Exported ${exported} proposal(s) for skill approval.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Export failed");
    } finally {
      setBusy(false);
    }
  };

  const sendInterview = async () => {
    if (!audit || !interviewInput.trim()) return;
    setBusy(true);
    try {
      const response = await ceApi(`/api/agent-os/audit/${audit.audit_id}/continue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: interviewInput.trim() }),
      });
      if (!response.ok) throw new Error("Interview step failed");
      const payload = (await response.json()) as { audit: Audit; reply: string; done: boolean };
      setAudit(payload.audit);
      setInterviewLog(payload.audit.interview_transcript || []);
      setInterviewInput("");
      if (payload.done) setMessage("Interview captured tasks. Complete the audit to generate proposals.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Interview failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="Workflow audit"
        description="Codify repeated work into skill candidates (Agent OS Level 1)."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Agent OS", href: "/agent-os/glass" },
          { label: "Workflow audit" },
        ]}
      />

      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Tab label="Manual" />
        <Tab label="Session scan" />
        <Tab label="Interview" />
      </Tabs>

      {tab === 0 && (
        <Box sx={{ display: "grid", gap: 2, maxWidth: 960 }}>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
            {domains.map((item) => (
              <Chip key={item} label={item} color={domain === item ? "primary" : "default"} onClick={() => setDomain(item)} />
            ))}
          </Box>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 180px" } }}>
            <TextField label="Task" value={description} onChange={(event) => setDescription(event.target.value)} multiline minRows={2} />
            <TextField select label="Frequency" value={frequency} onChange={(event) => setFrequency(event.target.value)}>
              {frequencies.map((item) => (
                <MenuItem key={item} value={item}>
                  {item.replace("_", " ")}
                </MenuItem>
              ))}
            </TextField>
          </Box>
          <TextField label="Desired output" value={desiredOutput} onChange={(event) => setDesiredOutput(event.target.value)} />
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <Button disabled={busy} variant="contained" startIcon={<PlayArrowIcon />} onClick={() => void runStart("manual")}>
              Start manual audit
            </Button>
            <Button disabled={!audit || busy || !description.trim()} startIcon={<AddIcon />} onClick={() => void addManualTask()}>
              Add task
            </Button>
          </Box>
        </Box>
      )}

      {tab === 1 && (
        <Box sx={{ display: "grid", gap: 2, maxWidth: 720 }}>
          <Typography variant="body2" color="text.secondary">
            Scan recent sessions for repeated requests and tools used.
          </Typography>
          <Slider
            value={sessionCount}
            min={5}
            max={50}
            step={5}
            marks
            valueLabelDisplay="auto"
            onChange={(_, value) => setSessionCount(Array.isArray(value) ? value[0] : value)}
          />
          <Button disabled={busy} variant="contained" startIcon={<PlayArrowIcon />} onClick={() => void runStart("session_scan")}>
            Scan sessions
          </Button>
        </Box>
      )}

      {tab === 2 && (
        <Box sx={{ display: "grid", gap: 2, maxWidth: 860 }}>
          <Button disabled={busy} variant="contained" startIcon={<PlayArrowIcon />} onClick={() => void runStart("interview")}>
            Start interview
          </Button>
          <TextField
            label="Answer"
            value={interviewInput}
            onChange={(event) => setInterviewInput(event.target.value)}
            multiline
            minRows={3}
          />
          <Button disabled={!audit || busy || !interviewInput.trim()} startIcon={<SendIcon />} onClick={() => void sendInterview()}>
            Send
          </Button>
          <Box sx={{ display: "grid", gap: 1 }}>
            {interviewLog.map((item, index) => (
              <Typography key={`${item.role}-${index}`} variant="body2">
                <strong>{item.role}:</strong> {item.content}
              </Typography>
            ))}
          </Box>
        </Box>
      )}

      {audit && (
        <Box sx={{ display: "grid", gap: 2 }}>
          <Typography variant="h6">Tasks ({audit.tasks?.length || 0})</Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Task</TableCell>
                <TableCell>Domain</TableCell>
                <TableCell>Frequency</TableCell>
                <TableCell>Skill</TableCell>
                <TableCell>Automation</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(audit.tasks || []).map((task) => (
                <TableRow key={task.id}>
                  <TableCell sx={{ minWidth: 260 }}>
                    <Typography variant="body2">{task.description}</Typography>
                    {task.tools_hint?.length ? (
                      <Typography variant="caption" color="text.secondary">
                        {task.tools_hint.join(", ")}
                      </Typography>
                    ) : null}
                  </TableCell>
                  <TableCell>{task.domain}</TableCell>
                  <TableCell>{task.frequency.replace("_", " ")}</TableCell>
                  <TableCell>
                    <FormControlLabel
                      control={<Checkbox checked={task.propose_skill} onChange={(event) => void updateTask(task.id, { propose_skill: event.target.checked })} />}
                      label=""
                    />
                  </TableCell>
                  <TableCell>
                    <FormControlLabel
                      control={<Checkbox checked={task.propose_automation} onChange={(event) => void updateTask(task.id, { propose_automation: event.target.checked })} />}
                      label=""
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <Button disabled={busy} variant="outlined" startIcon={<PlayArrowIcon />} onClick={() => void finishAudit()}>
              Complete
            </Button>
            <Button disabled={busy || audit.status !== "completed"} startIcon={<UploadFileIcon />} onClick={() => void exportAudit()}>
              Export proposals
            </Button>
            <Button startIcon={<DownloadIcon />} onClick={() => downloadAudit(audit)}>
              Download JSON
            </Button>
          </Box>
          {audit.status === "completed" && (
            <Typography variant="body2" color="text.secondary">
              {audit.proposed_skills.length} skill proposal(s), {audit.proposed_automations?.length || 0} automation candidate(s).
            </Typography>
          )}
        </Box>
      )}

      {message && <Typography color="text.secondary">{message}</Typography>}
    </Box>
  );
}
