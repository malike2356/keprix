"use client";

import JobCard from "@/components/ui/JobCard";
import type { StatusKey } from "@/theme/tokens/status";

export type ModelRunData = {
  id: string;
  name: string;
  status: StatusKey;
  model?: string;
  dataset?: string;
  lastRunAt?: string | null;
};

type ModelRunCardProps = {
  run: ModelRunData;
  onOpen?: (id: string) => void;
};

export default function ModelRunCard({ run, onOpen }: ModelRunCardProps) {
  const name = run.model ? `${run.name} (${run.model})` : run.name;
  return (
    <JobCard
      id={run.id}
      name={name}
      status={run.status}
      lastRunAt={run.lastRunAt}
      schedule={run.dataset ? `Dataset: ${run.dataset}` : undefined}
      onClick={onOpen ? () => onOpen(run.id) : undefined}
    />
  );
}
