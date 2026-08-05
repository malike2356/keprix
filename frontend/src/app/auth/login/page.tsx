"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import AuthLayout from "@/components/auth/AuthLayout";
import LoginForm from "@/components/auth/LoginForm";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import { useCESession } from "@/lib/ce-auth";

function safeReturnPath(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/home";
  }
  return value;
}

function AuthLoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnTo = safeReturnPath(searchParams.get("next"));
  const { user, isLoading } = useCESession();

  React.useEffect(() => {
    if (!isLoading && user) {
      router.replace(returnTo);
    }
  }, [isLoading, user, router, returnTo]);

  return (
    <AuthLayout>
      <Typography variant="h5" gutterBottom>
        Sign in
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Access your Keprix workspace.
      </Typography>
      <LoginForm returnTo={returnTo} />
    </AuthLayout>
  );
}

export default function AuthLoginPage() {
  return (
    <React.Suspense fallback={<Box sx={{ p: 4 }}><SkeletonDetailPanel fields={3} /></Box>}>
      <AuthLoginContent />
    </React.Suspense>
  );
}
