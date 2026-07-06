"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { createReviewRequest, fetchReviewRequests } from "@/lib/review-gateway-api";

export default function ReviewGatewayPage() {
  const { data, mutate } = useSWR("review-requests", fetchReviewRequests);
  const [title, setTitle] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);

  const handleCreate = async () => {
    const created = await createReviewRequest({
      title,
      context_message: "Please review the attached artifact.",
      artifact_type: "markdown",
      artifact_content: `# ${title}\n\nPending external review.`,
      reviewer_name: "Reviewer",
      reviewer_email: email,
      allowed_actions: ["approve", "reject", "request_change"],
    });
    setMessage(`Review link created: ${created.review_url}`);
    setTitle("");
    setEmail("");
    await mutate();
  };

  return (
    <Box>
      <PageHeader
        title="Review gateway"
        description="Request sign-off from external reviewers without Keprix accounts."
      />
      {message ? <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert> : null}
      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            New review request
          </Typography>
          <TextField label="Title" value={title} onChange={(e) => setTitle(e.target.value)} fullWidth sx={{ mb: 2 }} />
          <TextField
            label="Reviewer email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            fullWidth
            sx={{ mb: 2 }}
          />
          <Button variant="contained" disabled={!title || !email} onClick={() => void handleCreate()}>
            Create request
          </Button>
        </CardContent>
      </Card>
      <Card variant="outlined">
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Title</TableCell>
                <TableCell>Reviewer</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Decision</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(data?.requests ?? []).map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{row.title}</TableCell>
                  <TableCell>{row.reviewer_name}</TableCell>
                  <TableCell>{row.status}</TableCell>
                  <TableCell>{row.decision?.action || "-"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Box>
  );
}
