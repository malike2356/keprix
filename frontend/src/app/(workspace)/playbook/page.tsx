"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import MemoryIcon from "@mui/icons-material/Memory";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonStatGrid } from "@/components/ui/loading";
import {
  listPlaybookModels,
  listServing,
  scanHardware,
  serveModel,
  startModelDownload,
  type HardwareScan,
  type PlaybookModel,
} from "@/lib/playbook-api";

function fitColor(score: number): "success" | "warning" | "error" | "default" {
  if (score >= 0.9) {
    return "success";
  }
  if (score >= 0.6) {
    return "warning";
  }
  if (score >= 0.3) {
    return "default";
  }
  return "error";
}

export default function PlaybookPage() {
  const [hardware, setHardware] = React.useState<HardwareScan | null>(null);
  const [models, setModels] = React.useState<PlaybookModel[]>([]);
  const [serving, setServing] = React.useState<Array<{ model_id: string; backend: string; port: number }>>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [actionModelId, setActionModelId] = React.useState<string | null>(null);

  const loadScan = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [scan, catalog, active] = await Promise.all([
        scanHardware(),
        listPlaybookModels(),
        listServing(),
      ]);
      setHardware(scan);
      setModels(catalog.models);
      setServing(active);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleDownload = async (modelId: string) => {
    setActionModelId(modelId);
    setError(null);
    try {
      await startModelDownload(modelId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setActionModelId(null);
    }
  };

  const handleServe = async (modelId: string) => {
    setActionModelId(modelId);
    setError(null);
    try {
      await serveModel(modelId);
      const active = await listServing();
      setServing(active);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Serve failed");
    } finally {
      setActionModelId(null);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Local Model Playbook"
        description="Scan hardware, download models, and manage local serving."
        breadcrumbs={[
          { label: "Workspace", href: "/launcher" },
          { label: "Playbook", href: "/playbook" },
        ]}
        actions={
          <Button variant="contained" onClick={loadScan} disabled={loading}>
            {loading ? "Scanning..." : "Scan hardware"}
          </Button>
        }
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading && (
        <Box sx={{ mb: 3 }}>
          <SkeletonStatGrid count={4} />
        </Box>
      )}

      {hardware && !loading && (
        <>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "repeat(4, 1fr)" },
              gap: 2,
              mb: 3,
            }}
          >
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">
                  RAM
                </Typography>
                <Typography variant="h6">{hardware.total_ram_gb} GB</Typography>
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">
                  GPU VRAM
                </Typography>
                <Typography variant="h6">
                  {hardware.has_gpu ? `${hardware.gpu_vram_gb} GB` : "CPU only"}
                </Typography>
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">
                  CPU
                </Typography>
                <Typography variant="h6">{hardware.cpu_cores} cores</Typography>
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">
                  Free disk
                </Typography>
                <Typography variant="h6">{hardware.free_disk_gb} GB</Typography>
              </CardContent>
            </Card>
          </Box>

          {serving.length > 0 && (
            <Box sx={{ mb: 2, display: "flex", flexWrap: "wrap", gap: 1 }}>
              {serving.map((entry) => (
                <Chip
                  key={entry.model_id}
                  color="success"
                  label={`${entry.model_id} on ${entry.backend}:${entry.port}`}
                />
              ))}
            </Box>
          )}

          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recommended models
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Model</TableCell>
                    <TableCell>Family</TableCell>
                    <TableCell align="right">VRAM req.</TableCell>
                    <TableCell align="right">Fit</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {models.map((model) => (
                    <TableRow key={model.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight={600}>
                          {model.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {model.quant}
                        </Typography>
                      </TableCell>
                      <TableCell>{model.family}</TableCell>
                      <TableCell align="right">{model.vram_gb} GB</TableCell>
                      <TableCell align="right">
                        <Chip
                          size="small"
                          color={fitColor(model.fit_score)}
                          label={model.fit_score.toFixed(2)}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          sx={{ mr: 1 }}
                          disabled={actionModelId === model.id}
                          onClick={() => handleDownload(model.id)}
                        >
                          Pull
                        </Button>
                        <Button
                          size="small"
                          variant="outlined"
                          disabled={actionModelId === model.id}
                          onClick={() => handleServe(model.id)}
                        >
                          Serve
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}

      {!hardware && !loading && (
        <EmptyState
          title="No hardware scan yet"
          description="Run a hardware scan to see fit scores, recommended models, and active serving ports."
          icon={<MemoryIcon sx={{ fontSize: 48 }} />}
          actionLabel="Scan hardware"
          onAction={loadScan}
        />
      )}
    </Box>
  );
}
