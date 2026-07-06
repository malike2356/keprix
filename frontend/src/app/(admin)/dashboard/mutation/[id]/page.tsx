"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import dynamic from "next/dynamic";
import PageContainer from "@/components/shared/PageContainer";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import DiffViewer from "@/components/mutation/DiffViewer";
import MutationQualityBadge from "@/components/mutation/MutationQualityBadge";
import CodeBlock from "@/components/workspace/blocks/CodeBlock";
import {
  fetchCodeDiff,
  fetchToolSource,
  useMutationDetail,
  useQualityHistory,
} from "@/lib/mutation-api";
import { formatTimeAgo } from "@/lib/time-ago";

const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

type MutationDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default function MutationDetailPage({ params }: MutationDetailPageProps) {
  const { id } = React.use(params);
  const { data: record, isLoading } = useMutationDetail(id);
  const { data: quality } = useQualityHistory(id);
  const [source, setSource] = React.useState<string | null>(null);
  const [diff, setDiff] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!record) return;
    if (record.tier === "tool") {
      void fetchToolSource(record.id)
        .then((payload) => setSource(payload.source_code))
        .catch(() => setSource(null));
    }
    if (record.tier === "code") {
      void fetchCodeDiff(record.id)
        .then((payload) => setDiff(payload.diff))
        .catch(() => setDiff(null));
    }
  }, [record]);

  if (isLoading || !record) {
    return (
      <PageContainer title="Mutation detail" description="Loading mutation record." padded={false}>
        <SkeletonDetailPanel fields={6} />
      </PageContainer>
    );
  }

  const sampleScores = (quality?.samples ?? []).map((sample) => sample.score).reverse();

  return (
    <PageContainer title={record.name} description={`${record.tier} mutation`} padded={false}>
      <Box sx={{ display: "grid", gap: 2 }}>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", alignItems: "center" }}>
          <Chip label={record.tier.toUpperCase()} size="small" />
          <Chip label={record.status} size="small" color={record.status === "approved" ? "success" : "warning"} />
          <MutationQualityBadge
            score={record.quality_score}
            useCount={record.use_count}
            status={record.status}
            samples={sampleScores}
          />
        </Box>

        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 2 }}>
          <Field label="Recorded" value={formatTimeAgo(record.recorded_at)} />
          <Field label="Trigger" value={record.trigger} />
          <Field label="Approved by" value={record.approved_by || "n/a"} />
          <Field label="Last used" value={record.last_used_at ? formatTimeAgo(record.last_used_at) : "never"} />
        </Box>

        {record.description ? (
          <Typography variant="body2">{record.description}</Typography>
        ) : null}

        {sampleScores.length > 0 ? (
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Quality history
            </Typography>
            <Chart
              type="area"
              height={180}
              series={[{ name: "Score", data: sampleScores }]}
              options={{
                chart: { toolbar: { show: false } },
                xaxis: { categories: (quality?.samples ?? []).map((sample) => sample.sampled_at.slice(5, 16)) },
                yaxis: { max: 1, min: 0 },
              }}
            />
          </Box>
        ) : null}

        {quality?.samples?.length ? (
          <Box component="table" sx={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th align="left">Time</th>
                <th align="left">Outcome</th>
                <th align="left">Score</th>
                <th align="left">Run</th>
              </tr>
            </thead>
            <tbody>
              {quality.samples.map((sample) => (
                <tr key={`${sample.sampled_at}-${sample.run_id}`}>
                  <td>{formatTimeAgo(sample.sampled_at)}</td>
                  <td>{sample.outcome}</td>
                  <td>{Math.round(sample.score * 100)}%</td>
                  <td>{sample.run_id || "n/a"}</td>
                </tr>
              ))}
            </tbody>
          </Box>
        ) : null}

        {source ? <CodeBlock language="python" content={source} /> : null}
        {diff ? <DiffViewer diff={diff} /> : null}

        <Button component={NextLink} href="/dashboard/mutation" variant="outlined">
          Back to governance
        </Button>
      </Box>
    </PageContainer>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2">{value}</Typography>
    </Box>
  );
}
