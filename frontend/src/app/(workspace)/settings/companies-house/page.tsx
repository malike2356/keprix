"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import NextLink from "next/link";
import * as React from "react";
import useSWR from "swr";
import CompaniesHouseKeyForm from "@/components/companies-house/CompaniesHouseKeyForm";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonList } from "@/components/ui/loading";
import { fetchCompaniesHouseStatus } from "@/lib/companies-house-api";

export default function CompaniesHouseSettingsPage() {
  const { data, error, isLoading, mutate } = useSWR("companies-house-settings", fetchCompaniesHouseStatus);

  return (
    <Box sx={{ maxWidth: 720 }}>
      <PageHeader
        title="Companies House"
        description="Manage the UK Companies House Public Data API key used by search and agent tools."
        breadcrumbs={[
          { label: "Settings", href: "/settings" },
          { label: "Companies House" },
        ]}
        actions={
          <Button component={NextLink} href="/companies-house" variant="outlined">
            Open search
          </Button>
        }
      />

      {isLoading ? <SkeletonList rows={3} /> : null}
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error instanceof Error ? error.message : "Could not load status"}
        </Alert>
      ) : null}

      <CompaniesHouseKeyForm status={data} forceOpen onSaved={async () => { await mutate(); }} />
    </Box>
  );
}
