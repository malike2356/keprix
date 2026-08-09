"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Link from "@mui/material/Link";
import Step from "@mui/material/Step";
import StepLabel from "@mui/material/StepLabel";
import Stepper from "@mui/material/Stepper";
import Typography from "@mui/material/Typography";
import * as React from "react";

type Props = {
  projectId: string;
  hasDataset?: boolean;
  hasVault?: boolean;
  onExportObsidian?: () => void;
};

const STEPS = [
  { key: "upload", label: "Upload your data" },
  { key: "analyze", label: "Run statistical analysis" },
  { key: "notes", label: "Export notes to Obsidian" },
  { key: "write", label: "Write up results" },
];

function activeStep(hasDataset: boolean, hasVault: boolean): number {
  if (!hasDataset) return 0;
  if (!hasVault) return 1;
  return 2;
}

export default function ResearchGettingStarted({
  projectId,
  hasDataset = false,
  hasVault = false,
  onExportObsidian,
}: Props) {
  const current = activeStep(hasDataset, hasVault);

  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Getting started
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Follow these steps to move from raw survey data to notes and reports. No coding required.
        </Typography>
        <Stepper activeStep={current} alternativeLabel sx={{ mb: 2 }}>
          {STEPS.map((step) => (
            <Step key={step.key}>
              <StepLabel>{step.label}</StepLabel>
            </Step>
          ))}
        </Stepper>
        <Box sx={{ display: "grid", gap: 1 }}>
          {current === 0 ? (
            <Typography variant="body2">
              Upload an SPSS (.sav), Excel, or CSV file in the <strong>Datasets</strong> section below.
            </Typography>
          ) : null}
          {current === 1 ? (
            <Typography variant="body2">
              Use <strong>Statistical analysis</strong> below for PSPP or jamovi, or open{" "}
              <Link component="a" href="/analytics">
                Quick analytics
              </Link>{" "}
              for charts.
            </Typography>
          ) : null}
          {current >= 2 ? (
            <Typography variant="body2">
              Register your Obsidian vault in <strong>Notes</strong>, then export project notes.
              {onExportObsidian ? (
                <>
                  {" "}
                  <Link component="button" variant="body2" onClick={onExportObsidian} sx={{ cursor: "pointer" }}>
                    Export to Obsidian now
                  </Link>
                </>
              ) : null}
            </Typography>
          ) : null}
          <Typography variant="caption" color="text.secondary">
            Project ID: {projectId}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
}
