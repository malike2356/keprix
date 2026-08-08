"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid2";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { IconPlayerPlay, IconUpload, IconUsers } from "@tabler/icons-react";
import NextLink from "next/link";
import { useCallback, useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import CrewMessageFeed from "@/components/teams/CrewMessageFeed";
import StatCard from "@/components/admin/StatCard";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonList } from "@/components/ui/loading";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import {
  fetchTeam,
  fetchTeams,
  fetchTeamYaml,
  fetchTeamRunEvents,
  importTeam,
  runTeam,
  SAMPLE_TEAM_YAML,
  type TeamRunEvent,
} from "@/lib/teams-api";

export default function AgentTeamsPage() {
  return (
    <Suspense>
      <AgentTeamsPageInner />
    </Suspense>
  );
}

function AgentTeamsPageInner() {
  const searchParams = useSearchParams();
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);
  const [yaml, setYaml] = useState(SAMPLE_TEAM_YAML);
  const [objective, setObjective] = useState("Ship the adoption smoke path");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<unknown>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [crewEvents, setCrewEvents] = useState<TeamRunEvent[]>([]);
  const [importing, setImporting] = useState(false);
  const [running, setRunning] = useState(false);

  const { data: teams = [], isLoading: teamsLoading, mutate: mutateTeams } = useSWR(
    "agent-teams",
    fetchTeams,
  );

  const { data: teamDetail, isLoading: detailLoading } = useSWR(
    selectedTeam ? `agent-team-${selectedTeam}` : null,
    () => fetchTeam(selectedTeam as string),
  );

  useEffect(() => {
    if (!selectedTeam && teams.length) {
      setSelectedTeam(teams[0]);
    }
  }, [teams, selectedTeam]);

  useEffect(() => {
    if (!selectedTeam) return;
    fetchTeamYaml(selectedTeam)
      .then(setYaml)
      .catch(() => {
        // Keep editor content if export fails.
      });
  }, [selectedTeam]);

  useEffect(() => {
    const team = searchParams.get("team");
    const run = searchParams.get("run");
    if (team) {
      setSelectedTeam(team);
    }
    if (run) {
      setActiveRunId(run);
    }
  }, [searchParams]);

  useEffect(() => {
    if (!selectedTeam || !activeRunId) {
      setCrewEvents([]);
      return;
    }
    let active = true;
    const load = async () => {
      try {
        const payload = await fetchTeamRunEvents(selectedTeam, activeRunId);
        if (active) {
          setCrewEvents(payload.events || []);
        }
      } catch {
        if (active) setCrewEvents([]);
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, [selectedTeam, activeRunId]);

  const handleImport = async () => {
    setImporting(true);
    setActionError(null);
    setActionMessage(null);
    try {
      const result = await importTeam(yaml);
      await mutateTeams();
      setSelectedTeam(result.name);
      setActionMessage(`Imported team "${result.name}" with ${result.tasks.length} task(s).`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImporting(false);
    }
  };

  const handleRun = async () => {
    if (!selectedTeam) return;
    setRunning(true);
    setActionError(null);
    setActionMessage(null);
    setRunResult(null);
    setCrewEvents([]);
    setActiveRunId(null);
    try {
      const result = await runTeam(selectedTeam, objective);
      setActiveRunId(result.run_id);
      setRunResult(result.state);
      setActionMessage(`Team "${result.name}" finished with status: ${result.status}.`);
      const eventsPayload = await fetchTeamRunEvents(selectedTeam, result.run_id);
      setCrewEvents(eventsPayload.events || []);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setRunning(false);
    }
  };

  const loadSample = useCallback(() => {
    setYaml(SAMPLE_TEAM_YAML);
    setSelectedTeam(null);
  }, []);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <PageHeader
        title="Agent Teams"
        description="Import CrewAI-style YAML crews, inspect roles and tasks, and run them through the playbook runtime. This provisions agent workflows, not human user accounts."
        actions={
          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Button component={NextLink} href="/settings/users" size="small" variant="text">
              Workspace users
            </Button>
            <Button component={NextLink} href="/agent-studio" size="small" variant="outlined">
              Agent Studio
            </Button>
            <Button component={NextLink} href="/playbooks" size="small" variant="outlined">
              Playbooks
            </Button>
          </Stack>
        }
      />

      <Alert severity="info" sx={{ mb: 0 }}>
        Agent teams are multi-agent automations defined in YAML (`/api/teams`). To onboard people to this
        instance, use{" "}
        <Button component={NextLink} href="/settings/users" size="small" sx={{ verticalAlign: "baseline", p: 0, minWidth: 0 }}>
          Workspace users
        </Button>
        .
      </Alert>

      {actionError ? (
        <Alert severity="error" onClose={() => setActionError(null)}>
          {actionError}
        </Alert>
      ) : null}
      {actionMessage ? (
        <Alert severity="success" onClose={() => setActionMessage(null)}>
          {actionMessage}
        </Alert>
      ) : null}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard
            title="Registered teams"
            value={teams.length}
            loading={teamsLoading}
            icon={<IconUsers size={22} stroke={1.75} />}
            color="primary"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard
            title="Roles in selected team"
            value={teamDetail?.roles.length ?? 0}
            loading={detailLoading}
            icon={<IconUsers size={22} stroke={1.75} />}
            color="secondary"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard
            title="Tasks in selected team"
            value={teamDetail?.tasks.length ?? 0}
            loading={detailLoading}
            icon={<IconPlayerPlay size={22} stroke={1.75} />}
            color="info"
          />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 4 }}>
          <DashboardCard title="Your teams" subtitle="Select a team to inspect or run">
            {teamsLoading ? (
              <SkeletonList rows={5} rowHeight={44} />
            ) : teams.length === 0 ? (
              <EmptyState
                title="No teams imported yet"
                description="Import a Crew YAML file to register your first multi-agent team."
                icon={<IconUsers size={40} stroke={1.5} />}
                actionLabel="Load sample YAML"
                onAction={loadSample}
              />
            ) : (
              <List dense disablePadding>
                {teams.map((team) => (
                  <ListItemButton
                    key={team}
                    selected={selectedTeam === team}
                    onClick={() => setSelectedTeam(team)}
                    sx={{ borderRadius: 1, mb: 0.5 }}
                  >
                    <ListItemText
                      primary={team}
                      secondary={selectedTeam === team ? "Selected" : "Click to inspect"}
                      primaryTypographyProps={{ fontWeight: 600 }}
                    />
                  </ListItemButton>
                ))}
              </List>
            )}
          </DashboardCard>

          {selectedTeam && teamDetail ? (
            <Box sx={{ mt: 2 }}>
              <DashboardCard title="Team structure" subtitle={selectedTeam}>
              <Stack spacing={2}>
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                    Roles
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    {teamDetail.roles.map((role) => (
                      <Chip key={role} label={role} size="small" variant="outlined" />
                    ))}
                  </Stack>
                </Box>
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                    Flow start
                  </Typography>
                  <Chip label={teamDetail.flow.start} size="small" color="primary" variant="outlined" />
                </Box>
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                    Tasks
                  </Typography>
                  <Stack spacing={1}>
                    {teamDetail.tasks.map((task) => (
                      <Box
                        key={task.id}
                        sx={{
                          p: 1.5,
                          border: 1,
                          borderColor: "divider",
                          borderRadius: 1,
                          bgcolor: "background.default",
                        }}
                      >
                        <Typography variant="subtitle2">{task.id}</Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                          Role: {task.role || "-"}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                          {task.description || "No description"}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </Box>
              </Stack>
            </DashboardCard>
            </Box>
          ) : null}
        </Grid>

        <Grid size={{ xs: 12, lg: 8 }}>
          <DashboardCard
            title="Import team YAML"
            subtitle="Paste or edit CrewAI-style YAML, then register it with the runtime"
            action={
              <Button size="small" variant="text" onClick={loadSample}>
                Load sample
              </Button>
            }
          >
            <TextField
              value={yaml}
              onChange={(event) => setYaml(event.target.value)}
              fullWidth
              multiline
              minRows={12}
              placeholder="name: my-team&#10;roles: ..."
              sx={{
                mb: 2,
                "& textarea": { fontFamily: "monospace", fontSize: "0.8rem", lineHeight: 1.6 },
              }}
            />
            <Button
              variant="contained"
              startIcon={<IconUpload size={16} stroke={1.75} />}
              disabled={importing || !yaml.trim()}
              onClick={() => void handleImport()}
            >
              {importing ? "Importing..." : "Import team"}
            </Button>
          </DashboardCard>

          <Box sx={{ mt: 2 }}>
            <DashboardCard title="Run team" subtitle="Execute the selected team against an objective">
            <Stack spacing={2}>
              <TextField
                select
                label="Team"
                value={selectedTeam || ""}
                onChange={(event) => setSelectedTeam(event.target.value || null)}
                fullWidth
                SelectProps={{ native: true }}
                disabled={!teams.length}
              >
                <option value="">Select a team</option>
                {teams.map((team) => (
                  <option key={team} value={team}>
                    {team}
                  </option>
                ))}
              </TextField>
              <TextField
                label="Objective"
                value={objective}
                onChange={(event) => setObjective(event.target.value)}
                fullWidth
                placeholder="What should this team accomplish?"
              />
              <Button
                variant="contained"
                color="secondary"
                startIcon={<IconPlayerPlay size={16} stroke={1.75} />}
                disabled={running || !selectedTeam || !objective.trim()}
                onClick={() => void handleRun()}
              >
                {running ? "Running..." : "Run team"}
              </Button>
            </Stack>
          </DashboardCard>
          </Box>

          {(crewEvents.length > 0 || activeRunId) ? (
            <Box sx={{ mt: 2 }}>
              <DashboardCard
                title="Crew activity"
                subtitle={activeRunId ? `Run ${activeRunId}` : "Latest multi-agent trace"}
              >
                <CrewMessageFeed events={crewEvents} />
              </DashboardCard>
            </Box>
          ) : null}

          {runResult ? (
            <Box sx={{ mt: 2 }}>
              <DashboardCard title="Run state" subtitle="Latest playbook execution state">
                <StructuredDataView value={runResult} />
              </DashboardCard>
            </Box>
          ) : null}
        </Grid>
      </Grid>
    </Box>
  );
}
