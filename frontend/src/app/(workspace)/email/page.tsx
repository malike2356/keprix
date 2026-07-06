"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import EmailIcon from "@mui/icons-material/Email";
import RefreshIcon from "@mui/icons-material/Refresh";
import StarIcon from "@mui/icons-material/Star";
import StarBorderIcon from "@mui/icons-material/StarBorder";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonDetailPanel, SkeletonList } from "@/components/ui/loading";
import {
  createAiReplyDraft,
  fetchAiSummary,
  fetchEmail,
  fetchEmailAccounts,
  fetchInbox,
  markEmailRead,
  toggleEmailStar,
  triggerEmailSync,
  type EmailAccount,
  type EmailMessage,
} from "@/lib/email-api";

function priorityColor(priority: string): "error" | "warning" | "default" {
  if (priority === "high" || priority === "urgent") {
    return "error";
  }
  if (priority === "low") {
    return "default";
  }
  return "warning";
}

export default function EmailPage() {
  const [accounts, setAccounts] = React.useState<EmailAccount[]>([]);
  const [messages, setMessages] = React.useState<EmailMessage[]>([]);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [selected, setSelected] = React.useState<EmailMessage | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [detailLoading, setDetailLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [aiLoading, setAiLoading] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [acct, inbox] = await Promise.all([fetchEmailAccounts(), fetchInbox()]);
      setAccounts(acct);
      setMessages(inbox);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load email");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  const openMessage = async (message: EmailMessage) => {
    setSelectedId(message.id);
    setDetailLoading(true);
    setError(null);
    try {
      const full = await fetchEmail(message.id);
      setSelected(full);
      if (!full.is_read) {
        await markEmailRead(message.id);
        setMessages((prev) =>
          prev.map((row) => (row.id === message.id ? { ...row, is_read: true } : row)),
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open email");
    } finally {
      setDetailLoading(false);
    }
  };

  const handleSync = async () => {
    setError(null);
    try {
      await triggerEmailSync();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    }
  };

  const handleAiSummary = async () => {
    if (!selected) {
      return;
    }
    setAiLoading(true);
    setError(null);
    try {
      const result = await fetchAiSummary(selected.id);
      setSelected((prev) => (prev ? { ...prev, ai_summary: result.summary } : prev));
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI summary failed");
    } finally {
      setAiLoading(false);
    }
  };

  const handleAiDraft = async () => {
    if (!selected) {
      return;
    }
    setAiLoading(true);
    setError(null);
    try {
      await createAiReplyDraft(selected.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI draft failed");
    } finally {
      setAiLoading(false);
    }
  };

  const handleStar = async (emailId: string) => {
    try {
      const result = await toggleEmailStar(emailId);
      setMessages((prev) =>
        prev.map((row) => (row.id === emailId ? { ...row, is_starred: result.is_starred } : row)),
      );
      if (selected?.id === emailId) {
        setSelected((prev) => (prev ? { ...prev, is_starred: result.is_starred } : prev));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to toggle star");
    }
  };

  return (
    <Box>
      <PageHeader
        title="Email"
        description="Triage inbox threads with AI summaries."
        breadcrumbs={[
          { label: "Workspace", href: "/launcher" },
          { label: "Email", href: "/email" },
        ]}
        actions={
          <Button startIcon={<RefreshIcon />} onClick={handleSync} disabled={loading}>
            Sync
          </Button>
        }
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "200px 280px 1fr", lg: "220px 320px 1fr" },
          gap: 2,
          minHeight: 480,
        }}
      >
        <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.5 }}>
          <Typography variant="subtitle2" gutterBottom>
            Accounts
          </Typography>
          {accounts.length === 0 ? (
            <Typography variant="caption" color="text.secondary">
              No accounts configured. Add one in Settings.
            </Typography>
          ) : (
            <List dense disablePadding>
              {accounts.map((account) => (
                <ListItemText
                  key={account.id}
                  primary={account.label}
                  secondary={account.email_address}
                  sx={{ py: 0.5 }}
                />
              ))}
            </List>
          )}
        </Box>

        <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, overflow: "hidden" }}>
          {loading ? (
            <SkeletonList rows={8} rowHeight={64} />
          ) : messages.length === 0 ? (
            <EmptyState
              title="Inbox is empty"
              description="Connect an email account or sync to load messages."
              icon={<EmailIcon sx={{ fontSize: 40 }} />}
            />
          ) : (
            <List dense disablePadding sx={{ maxHeight: 520, overflow: "auto" }}>
              {messages.map((message) => (
                <ListItemButton
                  key={message.id}
                  selected={selectedId === message.id}
                  onClick={() => openMessage(message)}
                  sx={{ alignItems: "flex-start" }}
                >
                  <ListItemText
                    primary={
                      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                        <Typography
                          variant="body2"
                          fontWeight={message.is_read ? 400 : 700}
                          noWrap
                          sx={{ flex: 1 }}
                        >
                          {message.subject || "(no subject)"}
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStar(message.id);
                          }}
                        >
                          {message.is_starred ? (
                            <StarIcon fontSize="small" color="warning" />
                          ) : (
                            <StarBorderIcon fontSize="small" />
                          )}
                        </IconButton>
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="caption" color="text.secondary" noWrap display="block">
                          {message.from_name || message.from_address}
                        </Typography>
                        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 0.5 }}>
                          {message.ai_priority && message.ai_priority !== "normal" && (
                            <Chip size="small" label={message.ai_priority} color={priorityColor(message.ai_priority)} />
                          )}
                          {message.ai_tags?.slice(0, 2).map((tag) => (
                            <Chip key={tag} size="small" label={tag} variant="outlined" />
                          ))}
                        </Box>
                      </Box>
                    }
                  />
                </ListItemButton>
              ))}
            </List>
          )}
        </Box>

        <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 2, minHeight: 320 }}>
          {detailLoading ? (
            <SkeletonDetailPanel fields={4} />
          ) : selected ? (
            <>
              <Typography variant="h6" gutterBottom>
                {selected.subject}
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                From: {selected.from_name || selected.from_address}
              </Typography>
              <Divider sx={{ my: 2 }} />
              <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", mb: 2 }}>
                {selected.body_text || selected.preview || ""}
              </Typography>
              <Box sx={{ bgcolor: "action.hover", borderRadius: 1, p: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  AI summary
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {selected.ai_summary || "No summary yet. Generate one with AI."}
                </Typography>
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<AutoAwesomeIcon />}
                    disabled={aiLoading}
                    onClick={handleAiSummary}
                  >
                    Summarize
                  </Button>
                  <Button size="small" variant="contained" disabled={aiLoading} onClick={handleAiDraft}>
                    AI reply draft
                  </Button>
                </Box>
              </Box>
            </>
          ) : (
            <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
              Select a message to read
            </Typography>
          )}
        </Box>
      </Box>
    </Box>
  );
}
