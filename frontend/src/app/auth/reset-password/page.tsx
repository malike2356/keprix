"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import * as React from "react";
import AuthLayout from "@/components/auth/AuthLayout";
import ResetPasswordForm from "@/components/auth/ResetPasswordForm";
import { SkeletonDetailPanel } from "@/components/ui/loading";

function ResetPasswordContent() {
  return (
    <AuthLayout>
      <Typography variant="h5" gutterBottom>
        Reset password
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Set a new password for your account.
      </Typography>
      <ResetPasswordForm />
    </AuthLayout>
  );
}

export default function ResetPasswordPage() {
  return (
    <React.Suspense fallback={<Box sx={{ p: 4 }}><SkeletonDetailPanel fields={3} /></Box>}>
      <ResetPasswordContent />
    </React.Suspense>
  );
}
