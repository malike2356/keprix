"use client";

import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import DashboardCard from "@/components/cards/DashboardCard";
import type { BillingPlan } from "@/lib/billing-api";
import { formatFeatureValue } from "@/lib/billing-format";

type BillingPlanCompareProps = {
  plans: BillingPlan[];
  featureMatrix: Record<string, Record<string, unknown>>;
};

function collectFeatureKeys(plans: BillingPlan[], matrix: Record<string, Record<string, unknown>>): string[] {
  const keys = new Set<string>();
  for (const plan of plans) {
    Object.keys(plan.feature_flags || {}).forEach((key) => keys.add(key));
  }
  Object.values(matrix).forEach((flags) => {
    Object.keys(flags || {}).forEach((key) => keys.add(key));
  });
  return Array.from(keys).sort();
}

export default function BillingPlanCompare({ plans, featureMatrix }: BillingPlanCompareProps) {
  const features = collectFeatureKeys(plans, featureMatrix);
  if (plans.length === 0 || features.length === 0) return null;

  return (
    <DashboardCard title="Feature comparison">
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Feature</TableCell>
              {plans.map((plan) => (
                <TableCell key={plan.id} align="center">
                  {plan.name}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {features.map((feature) => (
              <TableRow key={feature}>
                <TableCell sx={{ textTransform: "capitalize" }}>{feature.replace(/_/g, " ")}</TableCell>
                {plans.map((plan) => {
                  const value =
                    featureMatrix[plan.id]?.[feature] ?? plan.feature_flags?.[feature];
                  return (
                    <TableCell key={`${plan.id}-${feature}`} align="center">
                      <Typography variant="body2">{formatFeatureValue(value)}</Typography>
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </DashboardCard>
  );
}
