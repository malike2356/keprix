"use client";

import AccountTreeIcon from "@mui/icons-material/AccountTree";
import CheckIcon from "@mui/icons-material/Check";
import DownloadIcon from "@mui/icons-material/Download";
import UploadIcon from "@mui/icons-material/Upload";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import PublishIcon from "@mui/icons-material/Publish";
import SaveIcon from "@mui/icons-material/Save";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { fetchEdition, isFeatureEnabled } from "@/lib/edition";

type Props = {
  id: string;
  name: string;
  busy: boolean;
  status: string | null;
  onMetaChange: (patch: { id?: string; name?: string }) => void;
  onSave: () => void;
  onRun: () => void;
  onExport: () => void;
  onExportBundle: () => void;
  onImportYaml: (text: string) => void;
  onImportN8n: (workflow: Record<string, unknown>) => void;
  onValidate: () => void;
  onPublish: (options: {
    scope: "personal" | "org";
    note: string;
    require_scout_approval: boolean;
  }) => void;
  onAutoLayout: () => void;
  readOnly?: boolean;
};

export default function StudioToolbar({
  id,
  name,
  busy,
  status,
  onMetaChange,
  onSave,
  onRun,
  onExport,
  onExportBundle,
  onImportYaml,
  onImportN8n,
  onValidate,
  onPublish,
  onAutoLayout,
  readOnly,
}: Props) {
  const [publishOpen, setPublishOpen] = React.useState(false);
  const [publishScope, setPublishScope] = React.useState<"personal" | "org">("personal");
  const [publishNote, setPublishNote] = React.useState("");
  const [requireScout, setRequireScout] = React.useState(false);
  const { data: edition } = useSWR("edition-info", fetchEdition);
  const orgPublishEnabled = isFeatureEnabled(edition, "org_playbook_publish");

  return (
    <>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          borderBottom: "1px solid",
          borderColor: "divider",
          p: 1,
          flexWrap: "wrap",
        }}
      >
        <TextField
          size="small"
          label="ID"
          value={id}
          onChange={(event) => onMetaChange({ id: event.target.value })}
          sx={{ width: 180 }}
        />
        <TextField
          size="small"
          label="Name"
          value={name}
          onChange={(event) => onMetaChange({ name: event.target.value })}
          sx={{ width: 240 }}
        />
        <Button size="small" startIcon={<SaveIcon />} disabled={busy || readOnly} onClick={onSave}>
          Save
        </Button>
        <Button size="small" startIcon={<PlayArrowIcon />} disabled={busy} onClick={onRun}>
          Run
        </Button>
        <Button size="small" startIcon={<CheckIcon />} disabled={busy} onClick={onValidate}>
          Validate
        </Button>
        <Button size="small" startIcon={<DownloadIcon />} disabled={busy} onClick={onExport}>
          Export YAML
        </Button>
        <Button size="small" startIcon={<DownloadIcon />} disabled={busy} onClick={onExportBundle}>
          Export bundle
        </Button>
        <Button size="small" startIcon={<UploadIcon />} disabled={busy || readOnly} onClick={() => yamlInputRef.current?.click()}>
          Import YAML
        </Button>
        <Button size="small" startIcon={<UploadIcon />} disabled={busy || readOnly} onClick={() => n8nInputRef.current?.click()}>
          Import n8n
        </Button>
        <Button size="small" startIcon={<AccountTreeIcon />} disabled={busy || readOnly} onClick={onAutoLayout}>
          Auto layout
        </Button>
        <Button size="small" startIcon={<PublishIcon />} disabled={busy || readOnly} onClick={() => setPublishOpen(true)}>
          Publish
        </Button>
        <input
          ref={yamlInputRef}
          hidden
          type="file"
          accept=".yaml,.yml,text/yaml"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (!file) return;
            void file.text().then(onImportYaml);
            event.target.value = "";
          }}
        />
        <input
          ref={n8nInputRef}
          hidden
          type="file"
          accept=".json,application/json"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (!file) return;
            void file.text().then((text) => onImportN8n(JSON.parse(text) as Record<string, unknown>));
            event.target.value = "";
          }}
        />
        {status ? (
          <Typography variant="caption" color="text.secondary" sx={{ ml: "auto" }}>
            {status}
          </Typography>
        ) : null}
      </Box>
      <Dialog open={publishOpen} onClose={() => setPublishOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>Publish playbook</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <TextField
            select
            label="Scope"
            value={publishScope}
            onChange={(event) => setPublishScope(event.target.value as "personal" | "org")}
            fullWidth
          >
            <MenuItem value="personal">Personal</MenuItem>
            <MenuItem value="org" disabled={!orgPublishEnabled}>
              Organization
            </MenuItem>
          </TextField>
          {!orgPublishEnabled ? (
            <Typography variant="caption" color="text.secondary">
              Organization publish is available in Enterprise Edition.
            </Typography>
          ) : null}
          <TextField
            label="Note"
            value={publishNote}
            onChange={(event) => setPublishNote(event.target.value)}
            fullWidth
            multiline
            minRows={3}
          />
          <FormControlLabel
            control={<Checkbox checked={requireScout} onChange={(event) => setRequireScout(event.target.checked)} />}
            label="Require Scout approval"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPublishOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => {
              onPublish({
                scope: publishScope,
                note: publishNote,
                require_scout_approval: requireScout,
              });
              setPublishOpen(false);
            }}
          >
            Publish
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
  const yamlInputRef = React.useRef<HTMLInputElement | null>(null);
  const n8nInputRef = React.useRef<HTMLInputElement | null>(null);
