"use client";

import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import DataSectionTabs, {
  DATA_SECTIONS,
  dataHref,
  parseDataTab,
  type DataSectionTab,
} from "@/components/data/DataSectionTabs";
import PageHeader from "@/components/ui/PageHeader";

const RagPipelinePanel = dynamic(() => import("@/components/data/panels/RagPipelinePanel"), {
  loading: () => <PanelLoading />,
  ssr: false,
});
const LocalModelsPanel = dynamic(() => import("@/components/data/panels/LocalModelsPanel"), {
  loading: () => <PanelLoading />,
  ssr: false,
});
const VideoIngestPanel = dynamic(() => import("@/components/data/panels/VideoIngestPanel"), {
  loading: () => <PanelLoading />,
  ssr: false,
});
const AnalyticsPanel = dynamic(() => import("@/components/data/panels/AnalyticsPanel"), {
  loading: () => <PanelLoading />,
  ssr: false,
});
const UsagePanel = dynamic(() => import("@/components/data/panels/UsagePanel"), {
  loading: () => <PanelLoading />,
  ssr: false,
});
const ObservabilityPanel = dynamic(() => import("@/components/data/panels/ObservabilityPanel"), {
  loading: () => <PanelLoading />,
  ssr: false,
});
const DatasetsPanel = dynamic(() => import("@/components/data/panels/DatasetsPanel"), {
  loading: () => <PanelLoading />,
  ssr: false,
});
const JobsQueuePanel = dynamic(() => import("@/components/data/panels/JobsQueuePanel"), {
  loading: () => <PanelLoading />,
  ssr: false,
});
const MlWorkspacePanel = dynamic(() => import("@/components/data/panels/MlWorkspacePanel"), {
  loading: () => <PanelLoading />,
  ssr: false,
});
const DocumentExportPanel = dynamic(() => import("@/components/data/panels/DocumentExportPanel"), {
  loading: () => <PanelLoading />,
  ssr: false,
});

function PanelLoading() {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
      <CircularProgress size={28} />
    </Box>
  );
}

function PanelForTab({ tab }: { tab: DataSectionTab }) {
  switch (tab) {
    case "datasets":
      return <DatasetsPanel />;
    case "jobs":
      return <JobsQueuePanel />;
    case "ml":
      return <MlWorkspacePanel />;
    case "export":
      return <DocumentExportPanel />;
    case "rag":
      return <RagPipelinePanel />;
    case "models":
      return <LocalModelsPanel />;
    case "video":
      return <VideoIngestPanel />;
    case "analytics":
      return <AnalyticsPanel />;
    case "usage":
      return <UsagePanel />;
    case "observability":
      return <ObservabilityPanel />;
    default:
      return <DatasetsPanel />;
  }
}

export default function DataWorkspaceClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const rawTab = searchParams.get("tab");

  React.useEffect(() => {
    if ((rawTab || "").trim().toLowerCase() === "sheets") {
      router.replace("/crm/enrich");
    }
  }, [rawTab, router]);

  const tab = parseDataTab(rawTab);
  const meta = DATA_SECTIONS.find((section) => section.value === tab) || DATA_SECTIONS[0];

  const onTabChange = React.useCallback(
    (next: DataSectionTab) => {
      router.replace(dataHref(next), { scroll: false });
    },
    [router],
  );

  return (
    <Box>
      <PageHeader
        title={meta.title}
        description={meta.description}
        breadcrumbs={[{ label: "Data", href: "/data" }, { label: meta.label }]}
      />
      <DataSectionTabs value={tab} onChange={onTabChange} />
      <PanelForTab tab={tab} />
    </Box>
  );
}
