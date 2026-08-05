"use client";

import Typography from "@mui/material/Typography";
import AuthLayout from "@/components/auth/AuthLayout";
import ForgotPasswordForm from "@/components/auth/ForgotPasswordForm";

export default function ForgotPasswordPage() {
  return (
    <AuthLayout>
      <Typography variant="h5" gutterBottom>
        Forgot password
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Request a password reset link for your account.
      </Typography>
      <ForgotPasswordForm />
    </AuthLayout>
  );
}
