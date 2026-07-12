"use client";

import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { useSearchParams } from "next/navigation";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";

type Link = {
  link_id: string;
  skill_slug: string;
  automation_type: string;
  automation_id: string;
  edit_url: string;
};

const targets = [
  { id: "cron", label: "Cron job" },
  { id: "playbook", label: "Playbook" },
  { id: "agent_app", label: "Agent App" },
];

export default function PromoteSkillPage() {
  const search = useSearchParams();
  const [skillSlug, setSkillSlug] = React.useState(search.get("skill") || "");
  const [target, setTarget] = React.useState("cron");
  const [schedule, setSchedule] = React.useState("0 8 * * 1-5");
  const [name, setName] = React.useState("");
  const [deliverTo, setDeliverTo] = React.useState("local");
  const [links, setLinks] = React.useState<Link[]>([]);
  const [message, setMessage] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const loadLinks = React.useCallback(async () => {
    const url = skillSlug ? `/api/agent-os/links?skill=${encodeURIComponent(skillSlug)}` : "/api/agent-os/links";
    const response = await ceApi(url);
    if (!response.ok) return;
    const payload = (await response.json()) as { links: Link[] };
    setLinks(payload.links);
  }, [skillSlug]);

  React.useEffect(() => {
    void loadLinks();
  }, [loadLinks]);

  const promote = async () => {
    setBusy(true);
    try {
      const response = await ceApi("/api/agent-os/promote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          skill_slug: skillSlug,
          target,
          schedule: target === "playbook" ? null : schedule,
          name: name || null,
          deliver_to: target === "cron" ? deliverTo : null,
        }),
      });
      if (!response.ok) throw new Error(await response.text());
      const payload = (await response.json()) as { automation_type: string; id: string; edit_url: string };
      setMessage(`Created ${payload.automation_type}: ${payload.id}`);
      await loadLinks();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Promotion failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="Promote skill"
        description="Turn an approved skill into a scheduled job, playbook, or Agent App."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Agent OS", href: "/agent-os/glass" },
          { label: "Promote" },
        ]}
      />
      <Box sx={{ display: "grid", gap: 2, maxWidth: 760 }}>
        <TextField label="Skill slug" value={skillSlug} onChange={(event) => setSkillSlug(event.target.value)} />
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          {targets.map((item) => (
            <Chip key={item.id} label={item.label} color={target === item.id ? "primary" : "default"} onClick={() => setTarget(item.id)} />
          ))}
        </Box>
        <TextField label="Automation name" value={name} onChange={(event) => setName(event.target.value)} />
        {target !== "playbook" && <TextField label="Schedule" value={schedule} onChange={(event) => setSchedule(event.target.value)} />}
        {target === "cron" && (
          <TextField select label="Deliver to" value={deliverTo} onChange={(event) => setDeliverTo(event.target.value)}>
            <MenuItem value="local">Local</MenuItem>
            <MenuItem value="notification">Notification</MenuItem>
            <MenuItem value="origin">Origin</MenuItem>
          </TextField>
        )}
        <Button disabled={busy || !skillSlug.trim()} variant="contained" startIcon={<PlayArrowIcon />} onClick={() => void promote()}>
          Create automation
        </Button>
      </Box>
      <Typography variant="h6">Linked automations</Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Skill</TableCell>
            <TableCell>Type</TableCell>
            <TableCell>ID</TableCell>
            <TableCell>Edit</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {links.map((link) => (
            <TableRow key={link.link_id}>
              <TableCell>{link.skill_slug}</TableCell>
              <TableCell>{link.automation_type}</TableCell>
              <TableCell>{link.automation_id}</TableCell>
              <TableCell>{link.edit_url}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {message && <Typography color="text.secondary">{message}</Typography>}
    </Box>
  );
}
