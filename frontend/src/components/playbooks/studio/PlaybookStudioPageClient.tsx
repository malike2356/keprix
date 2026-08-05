"use client";

import PlaybookStudioShell from "@/components/playbooks/studio/PlaybookStudioShell";
import StudioHandoffGate from "@/components/playbooks/studio/StudioHandoffGate";

type Props = {
  playbookId: string;
  connectorId?: string;
  runId?: string;
};

export default function PlaybookStudioPageClient({ playbookId, connectorId, runId }: Props) {
  return (
    <StudioHandoffGate>
      <PlaybookStudioShell playbookId={playbookId} connectorId={connectorId} runId={runId} />
    </StudioHandoffGate>
  );
}
