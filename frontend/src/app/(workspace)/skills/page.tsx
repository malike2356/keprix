"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Switch from "@mui/material/Switch";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import AutoGraphIcon from "@mui/icons-material/AutoGraph";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonTable } from "@/components/ui/loading";
import { ceApi } from "@/lib/ce-api";
import { fetchUiContract } from "@/lib/ui-contract";

type SkillRow = {
  name: string;
  category?: string | null;
  description?: string;
  enabled: boolean;
};

async function fetchSkills(): Promise<SkillRow[]> {
  const response = await ceApi("/api/skills");
  if (!response.ok) throw new Error("Failed to load skills");
  return (await response.json()) as SkillRow[];
}

async function toggleSkill(name: string, enabled: boolean): Promise<void> {
  const response = await ceApi("/api/skills/toggle", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, enabled }),
  });
  if (!response.ok) throw new Error("Failed to toggle skill");
}

export default function SkillsPage() {
  const { data: contract } = useSWR("ui-contract", fetchUiContract);
  const { data: skills, isLoading, mutate } = useSWR("workspace-skills", fetchSkills);
  const empty = contract?.empty_states?.skills;

  const onToggle = async (skill: SkillRow) => {
    await toggleSkill(skill.name, !skill.enabled);
    await mutate();
  };

  if (isLoading) {
    return (
      <Box>
        <PageHeader title="Skills Hub" description="Browse installed skills and packs." />
        <SkeletonTable rows={8} columns={4} />
      </Box>
    );
  }

  if (!skills || skills.length === 0) {
    return (
      <Box>
        <PageHeader title="Skills Hub" description="Browse installed skills and packs." />
        <EmptyState
          title={empty?.title ?? "No skills installed"}
          description={empty?.description ?? "Install skill packs to extend agent capabilities."}
          icon={<AutoGraphIcon sx={{ fontSize: 48 }} />}
        />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader title="Skills Hub" description="Browse installed skills and packs." />
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Skill</TableCell>
            <TableCell>Category</TableCell>
            <TableCell>Description</TableCell>
            <TableCell align="right">Enabled</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {(skills ?? []).map((skill) => (
            <TableRow key={skill.name}>
              <TableCell>
                <Typography variant="body2" fontWeight={600}>
                  {skill.name}
                </Typography>
              </TableCell>
              <TableCell>
                <Chip size="small" label={skill.category || "uncategorized"} />
              </TableCell>
              <TableCell>
                <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 420 }}>
                  {skill.description || ";"}
                </Typography>
              </TableCell>
              <TableCell align="right">
                <Switch checked={skill.enabled} onChange={() => onToggle(skill)} size="small" />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}
