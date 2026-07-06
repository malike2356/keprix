"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import type { AgentRole } from "@/lib/multiagent-api";

const POLICIES = [
  "round_robin",
  "supervisor_moderated",
  "vote_decide",
  "debate_summarize",
  "human_review",
];

type AgentRolePanelProps = {
  roles: AgentRole[];
  selectedRole: string | null;
  onSelectRole: (role: string) => void;
  policy: string;
  onPolicyChange: (policy: string) => void;
  supervisor: string;
  onSupervisorChange: (supervisor: string) => void;
  playbookName: string;
  onPlaybookNameChange: (name: string) => void;
  onConnect: () => void;
};

export default function AgentRolePanel({
  roles,
  selectedRole,
  onSelectRole,
  policy,
  onPolicyChange,
  supervisor,
  onSupervisorChange,
  playbookName,
  onPlaybookNameChange,
  onConnect,
}: AgentRolePanelProps) {
  const roleNames = roles.map((item) => item.name);
  const selectedValue = selectedRole && roleNames.includes(selectedRole) ? selectedRole : "";
  const supervisorValue = supervisor && roleNames.includes(supervisor) ? supervisor : "";
  const role = roles.find((item) => item.name === selectedValue);

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" sx={{ mb: 2 }}>
          Roles and policy
        </Typography>
        <TextField
          fullWidth
          size="small"
          label="Playbook name"
          value={playbookName}
          onChange={(event) => onPlaybookNameChange(event.target.value)}
          sx={{ mb: 2 }}
        />
        <TextField
          select
          fullWidth
          size="small"
          label="Selected role"
          value={selectedValue}
          onChange={(event) => onSelectRole(event.target.value)}
          sx={{ mb: 2 }}
          SelectProps={{ displayEmpty: true }}
        >
          <MenuItem value="">
            <em>Select a role</em>
          </MenuItem>
          {roles.map((item) => (
            <MenuItem key={item.name} value={item.name}>
              {item.name}
            </MenuItem>
          ))}
        </TextField>
        {role ? (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2">{role.goal}</Typography>
            <Typography variant="caption" color="text.secondary">
              Tools: {(role.tools ?? []).join(", ") || "none"}
            </Typography>
          </Box>
        ) : null}
        <TextField
          select
          fullWidth
          size="small"
          label="Group chat policy"
          value={policy}
          onChange={(event) => onPolicyChange(event.target.value)}
          sx={{ mb: 2 }}
        >
          {POLICIES.map((item) => (
            <MenuItem key={item} value={item}>
              {item}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          fullWidth
          size="small"
          label="Supervisor"
          value={supervisorValue}
          onChange={(event) => onSupervisorChange(event.target.value)}
          sx={{ mb: 2 }}
          SelectProps={{ displayEmpty: true }}
        >
          <MenuItem value="">
            <em>Select supervisor</em>
          </MenuItem>
          {roles.map((item) => (
            <MenuItem key={item.name} value={item.name}>
              {item.name}
            </MenuItem>
          ))}
        </TextField>
        <Button size="small" variant="outlined" onClick={onConnect} disabled={!selectedValue || !supervisorValue}>
          Connect supervisor to selected role
        </Button>
      </CardContent>
    </Card>
  );
}
