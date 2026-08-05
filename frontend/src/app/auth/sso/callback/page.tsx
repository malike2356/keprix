"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import AuthLayout from "@/components/auth/AuthLayout";
import { setCESession } from "@/lib/ce-api";
import { useCESession } from "@/lib/ce-auth";

function SsoCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refreshUser } = useCESession();
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const callbackError = searchParams.get("error");
    const linked = searchParams.get("linked");
    const token = searchParams.get("token");
    const returnTo = searchParams.get("return_to") || "/home";
    const safeReturn = returnTo.startsWith("/") && !returnTo.startsWith("//") ? returnTo : "/home";

    if (callbackError) {
      setError(callbackError);
      return;
    }

    if (linked) {
      router.replace(safeReturn);
      return;
    }

    if (!token) {
      setError("Missing sign-in token");
      return;
    }

    setCESession(token, { id: "", username: "", role: "user" });
    refreshUser()
      .then(() => router.replace(safeReturn))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to complete sign-in"));
  }, [refreshUser, router, searchParams]);

  return (
    <AuthLayout>
      <Typography variant="h5" gutterBottom>
        Signing you in
      </Typography>
      <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2, py: 4 }}>
        {error ? (
          <Alert severity="error">{error}</Alert>
        ) : (
          <>
            <CircularProgress size={32} />
            <Typography color="text.secondary">Completing single sign-on...</Typography>
          </>
        )}
      </Box>
    </AuthLayout>
  );
}

export default function SsoCallbackPage() {
  return (
    <React.Suspense
      fallback={
        <AuthLayout>
          <Typography variant="h5" gutterBottom>
            Signing you in
          </Typography>
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress size={32} />
          </Box>
        </AuthLayout>
      }
    >
      <SsoCallbackContent />
    </React.Suspense>
  );
}
