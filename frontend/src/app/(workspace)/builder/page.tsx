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
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import {
  fetchBuilderJobs,
  fetchBuilderProjects,
  fetchBuilderTemplates,
  scaffoldBuilderProject,
  scanBuilderProjects,
  startBuilderJob,
  type BuilderProject,
} from "@/lib/builder-api";

function statusColor(status: string): "success" | "warning" | "error" | "default" {
  if (status === "healthy") return "success";
  if (status === "wip" || status === "needs-update") return "warning";
  if (status === "broken") return "error";
  return "default";
}

function ProjectCard({
  project,
  onBuild,
}: {
  project: BuilderProject;
  onBuild: (project: BuilderProject) => void;
}) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1, mb: 1 }}>
          <Typography variant="h6">{project.name}</Typography>
          <Chip size="small" label={project.stack_type || "unknown"} />
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {project.path}
        </Typography>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
          <Chip size="small" color={statusColor(project.status)} label={project.status} />
          {(project.tech_stack || []).slice(0, 4).map((tech) => (
            <Chip key={tech} size="small" variant="outlined" label={tech} />
          ))}
        </Box>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button size="small" variant="contained" onClick={() => onBuild(project)}>
            Build
          </Button>
          <Button size="small" component="a" href={`/builder?project=${project.id}`} variant="outlined">
            Details
          </Button>
          <Button
            size="small"
            component="a"
            href={`/design/preview?path=${encodeURIComponent(project.path)}`}
            variant="outlined"
          >
            Preview
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}

export default function BuilderPage() {
  const { data, mutate } = useSWR("builder-projects", fetchBuilderProjects);
  const { data: templatesData } = useSWR("builder-templates", fetchBuilderTemplates);
  const { data: jobsData, mutate: mutateJobs } = useSWR("builder-jobs", fetchBuilderJobs);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [buildProject, setBuildProject] = React.useState<BuilderProject | null>(null);
  const [instruction, setInstruction] = React.useState("");
  const [scaffoldOpen, setScaffoldOpen] = React.useState(false);
  const [template, setTemplate] = React.useState("keprix-nextjs-app");
  const [projectName, setProjectName] = React.useState("");
  const [scaffoldPath, setScaffoldPath] = React.useState("/tmp/keprix-scaffolds");

  const projects = data?.projects ?? [];
  const jobs = jobsData?.jobs ?? [];
  const templates = templatesData?.templates ?? [];

  const handleScan = async () => {
    setError(null);
    try {
      await scanBuilderProjects();
      await mutate();
      setMessage("Project scan complete");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
    }
  };

  const handleBuild = async () => {
    if (!buildProject) return;
    setError(null);
    try {
      const result = await startBuilderJob(buildProject.id, instruction);
      setBuildProject(null);
      setInstruction("");
      await mutateJobs();
      setMessage(`Build job started: ${result.job.id}`);
      window.location.href = `/builder/jobs/${result.job.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Build failed");
    }
  };

  const handleScaffold = async () => {
    setError(null);
    try {
      const result = await scaffoldBuilderProject({
        template,
        name: projectName,
        path: scaffoldPath,
      });
      setScaffoldOpen(false);
      await mutate();
      setMessage(`Scaffolded ${result.project.name} at ${result.result.path}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scaffold failed");
    }
  };

  return (
    <Box>
      <PageHeader
        title="Project Builder"
        description="Discover monorepo projects, scaffold new apps, and run agent build jobs."
      />
      {message ? <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert> : null}
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
        <Button variant="contained" onClick={() => void handleScan()}>
          Rescan projects
        </Button>
        <Button variant="outlined" onClick={() => setScaffoldOpen(true)}>
          New project
        </Button>
        <Button variant="outlined" component="a" href="/design/preview">
          Design preview
        </Button>
      </Box>
      <Typography variant="h6" sx={{ mb: 1 }}>
        Projects ({projects.length})
      </Typography>
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { md: "1fr 1fr" }, mb: 4 }}>
        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} onBuild={setBuildProject} />
        ))}
      </Box>
      <Typography variant="h6" sx={{ mb: 1 }}>
        Recent jobs ({jobs.length})
      </Typography>
      <Box sx={{ display: "grid", gap: 1 }}>
        {jobs.slice(0, 10).map((job) => (
          <Card key={job.id} variant="outlined">
            <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1 }}>
                <Typography variant="body2">{job.instruction}</Typography>
                <Chip size="small" label={job.status} />
              </Box>
              <Button size="small" component="a" href={`/builder/jobs/${job.id}`} sx={{ mt: 1 }}>
                View log
              </Button>
            </CardContent>
          </Card>
        ))}
      </Box>

      <Dialog open={Boolean(buildProject)} onClose={() => setBuildProject(null)} fullWidth maxWidth="sm">
        <DialogTitle>Build {buildProject?.name}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            multiline
            minRows={3}
            label="Instruction"
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
            placeholder="add user export CSV feature"
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBuildProject(null)}>Cancel</Button>
          <Button variant="contained" disabled={!instruction.trim()} onClick={() => void handleBuild()}>
            Start build
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={scaffoldOpen} onClose={() => setScaffoldOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>New project</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <TextField select label="Template" value={template} onChange={(e) => setTemplate(e.target.value)}>
            {templates.map((item) => (
              <MenuItem key={item.name} value={item.name}>
                {item.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField label="Project name" value={projectName} onChange={(e) => setProjectName(e.target.value)} />
          <TextField label="Parent path" value={scaffoldPath} onChange={(e) => setScaffoldPath(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setScaffoldOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={!projectName.trim()} onClick={() => void handleScaffold()}>
            Scaffold
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
