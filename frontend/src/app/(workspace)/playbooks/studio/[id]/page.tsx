import { Suspense } from "react";
import PlaybookStudioPageClient from "@/components/playbooks/studio/PlaybookStudioPageClient";

type Props = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ connector?: string; run?: string; handoff?: string }>;
};

export default async function PlaybookStudioPage({ params, searchParams }: Props) {
  const { id } = await params;
  const { connector, run } = await searchParams;
  return (
    <Suspense fallback={null}>
      <PlaybookStudioPageClient
        playbookId={decodeURIComponent(id)}
        connectorId={connector ? decodeURIComponent(connector) : undefined}
        runId={run ? decodeURIComponent(run) : undefined}
      />
    </Suspense>
  );
}
