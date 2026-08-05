"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import * as React from "react";
import { fetchAdminTools, type AdminTool } from "@/lib/admin-workspace-api";
import type { StudioNode, StudioNodeData } from "@/lib/playbook-studio/canvas-types";
import { nodeDefinition } from "@/lib/playbook-studio/node-registry";

type Props = {
  node: StudioNode | null;
  onUpdate: (nodeId: string, data: Partial<StudioNodeData>) => void;
};

export default function NodeInspector({ node, onUpdate }: Props) {
  const [tools, setTools] = React.useState<AdminTool[]>([]);

  React.useEffect(() => {
    fetchAdminTools()
      .then((payload) => setTools(payload.items || []))
      .catch(() => setTools([]));
  }, []);

  if (!node) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="subtitle2">Inspector</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Select a node to edit its fields.
        </Typography>
      </Box>
    );
  }

  const definition = nodeDefinition(node.type);
  const Icon = definition.icon;
  const update = (data: Partial<StudioNodeData>) => onUpdate(node.id, data);

  return (
    <Box sx={{ p: 2, display: "grid", gap: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Icon fontSize="small" />
        <Typography variant="subtitle2">{definition.label}</Typography>
      </Box>
      <TextField
        size="small"
        label="Label"
        value={node.data.label || ""}
        onChange={(event) => update({ label: event.target.value })}
        fullWidth
      />
      {node.data.connector_id ? (
        <Chip
          component={Link}
          href={`/integrations?id=${encodeURIComponent(node.data.connector_id)}`}
          clickable
          label={`Connector: ${node.data.connector_id}`}
          variant="outlined"
        />
      ) : null}
      {node.type === "trigger" ? (
        <TextField
          size="small"
          label="Description"
          value={node.data.description || ""}
          onChange={(event) => update({ description: event.target.value })}
          fullWidth
          multiline
          minRows={3}
        />
      ) : null}
      {node.type === "agent_task" ? (
        <>
          <TextField
            label="Prompt"
            value={node.data.prompt || ""}
            onChange={(event) => update({ prompt: event.target.value })}
            fullWidth
            multiline
            minRows={6}
          />
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <Chip size="small" label="{{ steps.previous.output }}" />
            <Chip size="small" label="{{ steps.step_id.output }}" />
          </Box>
          <TextField
            select
            label="Tools"
            value={node.data.tools || []}
            onChange={(event) => {
              const value = event.target.value;
              update({ tools: typeof value === "string" ? value.split(",") : value });
            }}
            SelectProps={{ multiple: true }}
            fullWidth
          >
            {tools.map((tool) => (
              <MenuItem key={tool.id} value={tool.id}>
                {tool.name || tool.id}
              </MenuItem>
            ))}
          </TextField>
        </>
      ) : null}
      {node.type === "http" ? (
        <>
          <TextField
            size="small"
            label="URL"
            value={node.data.url || ""}
            onChange={(event) => update({ url: event.target.value })}
            fullWidth
          />
          <TextField
            select
            size="small"
            label="Method"
            value={node.data.method || "GET"}
            onChange={(event) => update({ method: event.target.value })}
            fullWidth
          >
            {["GET", "POST", "PUT", "PATCH", "DELETE"].map((method) => (
              <MenuItem key={method} value={method}>
                {method}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Body"
            value={node.data.body || ""}
            onChange={(event) => update({ body: event.target.value })}
            fullWidth
            multiline
            minRows={5}
          />
        </>
      ) : null}
      {node.type === "condition" ? (
        <>
          <TextField
            label="Expression"
            value={node.data.expression || ""}
            onChange={(event) => update({ expression: event.target.value })}
            fullWidth
            multiline
            minRows={3}
          />
          <TextField
            size="small"
            label="True branch"
            value={node.data.trueLabel || "True"}
            onChange={(event) => update({ trueLabel: event.target.value })}
            fullWidth
          />
          <TextField
            size="small"
            label="False branch"
            value={node.data.falseLabel || "False"}
            onChange={(event) => update({ falseLabel: event.target.value })}
            fullWidth
          />
        </>
      ) : null}
      {node.type === "human_approval" ? (
        <>
          <TextField
            label="Message"
            value={node.data.message || ""}
            onChange={(event) => update({ message: event.target.value })}
            fullWidth
            multiline
            minRows={4}
          />
          <TextField
            select
            size="small"
            label="Risk"
            value={node.data.risk || "medium"}
            onChange={(event) => update({ risk: event.target.value as StudioNodeData["risk"] })}
            fullWidth
          >
            {["low", "medium", "high"].map((risk) => (
              <MenuItem key={risk} value={risk}>
                {risk}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            size="small"
            label="Summary"
            value={node.data.summary || ""}
            onChange={(event) => update({ summary: event.target.value })}
            fullWidth
          />
        </>
      ) : null}
      {node.type === "artifact" ? (
        <>
          <TextField
            size="small"
            label="Artifact name"
            value={node.data.name || ""}
            onChange={(event) => update({ name: event.target.value })}
            fullWidth
          />
          <TextField
            label="Content"
            value={node.data.content || ""}
            onChange={(event) => update({ content: event.target.value })}
            fullWidth
            multiline
            minRows={4}
          />
          <TextField
            size="small"
            label="From state key"
            value={node.data.from_key || ""}
            onChange={(event) => update({ from_key: event.target.value })}
            fullWidth
          />
        </>
      ) : null}
      {node.type === "delay" ? (
        <TextField
          label="Message"
          value={node.data.message || ""}
          onChange={(event) => update({ message: event.target.value })}
          fullWidth
          multiline
          minRows={3}
        />
      ) : null}
      {node.type === "parallel" ? (
        <Typography variant="body2" color="text.secondary">
          Parallel branches run from the configured task list. Detailed branch editing is available in YAML.
        </Typography>
      ) : null}
    </Box>
  );
}
