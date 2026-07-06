"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import SystemUpdateAltIcon from "@mui/icons-material/SystemUpdateAlt";
import * as React from "react";
import { useRouter } from "next/navigation";
import {
  downloadAgentAppExport,
  isNewerVersion,
  uninstallAgentApp,
  upgradeAgentAppUpload,
  validateAgentAppUpload,
  type AgentAppDetail,
} from "@/lib/agent-apps-api";

type Props = {
  appName: string;
  app?: AgentAppDetail;
};

export default function AgentAppManageActions({ appName, app }: Props) {
  const router = useRouter();
  const [busy, setBusy] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [confirmUninstall, setConfirmUninstall] = React.useState(false);
  const [upgradeVersion, setUpgradeVersion] = React.useState<string | null>(null);
  const upgradeInputRef = React.useRef<HTMLInputElement>(null);

  const onExport = async () => {
    setBusy("export");
    setError(null);
    try {
      await downloadAgentAppExport(appName);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusy(null);
    }
  };

  const onUninstall = async () => {
    setBusy("uninstall");
    setError(null);
    try {
      await uninstallAgentApp(appName);
      setConfirmUninstall(false);
      router.push("/agent-apps");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Uninstall failed");
    } finally {
      setBusy(null);
    }
  };

  const onUpgradeFile = async (file: File | null) => {
    if (!file) return;
    setBusy("upgrade");
    setError(null);
    setUpgradeVersion(null);
    try {
      const validation = await validateAgentAppUpload(file);
      if (!validation.valid || !validation.manifest) {
        throw new Error(validation.error || "Invalid upgrade bundle");
      }
      if (validation.manifest.name !== appName) {
        throw new Error(
          `Bundle is for ${validation.manifest.name}, not ${appName}`,
        );
      }
      const installedVersion = app?.version || "0.0.0";
      if (!isNewerVersion(validation.manifest.version, installedVersion)) {
        throw new Error(
          `Bundle version ${validation.manifest.version} is not newer than installed v${installedVersion}`,
        );
      }
      setUpgradeVersion(validation.manifest.version);
      const result = await upgradeAgentAppUpload(appName, file);
      router.push(result.redirect || `/agent-apps/${appName}`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upgrade failed");
    } finally {
      setBusy(null);
      setUpgradeVersion(null);
    }
  };

  return (
    <Stack spacing={1}>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {upgradeVersion ? (
        <Typography variant="body2" color="text.secondary">
          Upgrading to v{upgradeVersion}...
        </Typography>
      ) : null}
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Button
          variant="outlined"
          size="small"
          startIcon={<FileDownloadIcon />}
          onClick={() => void onExport()}
          disabled={busy !== null}
        >
          {busy === "export" ? "Exporting..." : "Export bundle"}
        </Button>
        <Button
          variant="outlined"
          size="small"
          startIcon={<SystemUpdateAltIcon />}
          onClick={() => upgradeInputRef.current?.click()}
          disabled={busy !== null}
        >
          {busy === "upgrade" ? "Upgrading..." : "Upgrade"}
        </Button>
        <input
          ref={upgradeInputRef}
          type="file"
          accept=".zip,application/zip"
          hidden
          onChange={(event) => void onUpgradeFile(event.target.files?.[0] ?? null)}
        />
        <Button
          variant="outlined"
          color="error"
          size="small"
          startIcon={<DeleteOutlineIcon />}
          onClick={() => setConfirmUninstall(true)}
          disabled={busy !== null}
        >
          Uninstall
        </Button>
      </Stack>

      <Dialog open={confirmUninstall} onClose={() => setConfirmUninstall(false)}>
        <DialogTitle>Uninstall {app?.display_name || appName}?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This removes the app from your workspace and deletes its installed files. Run history
            may remain in the observability store.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmUninstall(false)}>Cancel</Button>
          <Button color="error" onClick={() => void onUninstall()} disabled={busy === "uninstall"}>
            {busy === "uninstall" ? "Removing..." : "Uninstall"}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
