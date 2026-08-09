"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid2";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import {
  IconAlertTriangle,
  IconBell,
  IconCheck,
  IconClock,
  IconSettings,
  IconShield,
} from "@tabler/icons-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import useSWR from "swr";
import StatCard from "@/components/admin/StatCard";
import { SkeletonList } from "@/components/ui/loading";
import DashboardCard from "@/components/cards/DashboardCard";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import { dateGroup, formatTimeAgo, type DateGroup } from "@/lib/time-ago";
import {
  fetchInbox,
  markAllNotificationsRead,
  markNotificationRead,
  type InboxNotification,
} from "@/lib/notifications-api";

type FilterTab = "all" | "unread";

const GROUP_ORDER: DateGroup[] = ["Today", "Yesterday", "Older"];

function severityColor(severity: string): "default" | "warning" | "error" | "info" {
  if (severity === "critical") return "error";
  if (severity === "warning") return "warning";
  if (severity === "info") return "info";
  return "default";
}

function typeIcon(type: string) {
  const normalized = type.toLowerCase();
  if (normalized.includes("security") || normalized.includes("vault")) {
    return <IconShield size={18} stroke={1.75} />;
  }
  if (normalized.includes("approval") || normalized.includes("mutation")) {
    return <IconAlertTriangle size={18} stroke={1.75} />;
  }
  if (normalized.includes("job") || normalized.includes("cron")) {
    return <IconClock size={18} stroke={1.75} />;
  }
  return <IconBell size={18} stroke={1.75} />;
}

function groupNotifications(items: InboxNotification[]) {
  const groups: Record<DateGroup, InboxNotification[]> = {
    Today: [],
    Yesterday: [],
    Older: [],
  };
  for (const item of items) {
    groups[dateGroup(item.created_at)].push(item);
  }
  return groups;
}

function NotificationCard({
  item,
  onRead,
}: {
  item: InboxNotification;
  onRead: (id: string) => Promise<void>;
}) {
  const router = useRouter();

  const handleOpen = async () => {
    if (!item.read) {
      await onRead(item.id);
    }
    if (item.href) {
      router.push(item.href);
    }
  };

  return (
    <Box
      sx={{
        p: 2,
        border: 1,
        borderColor: "divider",
        borderRadius: 1,
        bgcolor: item.read ? "background.paper" : "action.hover",
        borderLeft: item.read ? 1 : 3,
        borderLeftColor: item.read ? "divider" : "primary.main",
        cursor: item.href ? "pointer" : "default",
        "&:hover": item.href ? { bgcolor: "action.selected" } : undefined,
      }}
      onClick={() => {
        if (item.href) void handleOpen();
      }}
    >
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} justifyContent="space-between">
        <Stack direction="row" spacing={1.5} sx={{ minWidth: 0, flex: 1 }}>
          <Box sx={{ color: "text.secondary", pt: 0.25, flexShrink: 0 }}>{typeIcon(item.notification_type)}</Box>
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mb: 0.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: item.read ? 500 : 700 }}>
                {item.title}
              </Typography>
              {!item.read ? <Chip size="small" label="Unread" color="primary" variant="outlined" /> : null}
              <Chip size="small" label={item.notification_type.replace(/_/g, " ")} variant="outlined" />
              <Chip size="small" color={severityColor(item.severity)} label={item.severity} variant="outlined" />
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
              {item.message}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {formatTimeAgo(item.created_at)}
              {item.created_at ? ` · ${item.created_at.slice(0, 19).replace("T", " ")}` : ""}
            </Typography>
          </Box>
        </Stack>
        <Stack direction="row" spacing={1} alignItems="flex-start" sx={{ flexShrink: 0 }}>
          {!item.read ? (
            <Button
              size="small"
              variant="text"
              startIcon={<IconCheck size={14} stroke={1.75} />}
              onClick={(event) => {
                event.stopPropagation();
                void onRead(item.id);
              }}
            >
              Mark read
            </Button>
          ) : null}
          {item.href ? (
            <Button
              size="small"
              variant="outlined"
              component="a"
              href={item.href}
              onClick={(event) => {
                event.stopPropagation();
                if (!item.read) void onRead(item.id);
              }}
            >
              Open
            </Button>
          ) : null}
        </Stack>
      </Stack>
    </Box>
  );
}

export default function NotificationsPage() {
  const [filter, setFilter] = useState<FilterTab>("all");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [acting, setActing] = useState(false);

  const { data, isLoading, mutate } = useSWR("notifications-inbox", () => fetchInbox());

  const allNotifications = data?.notifications ?? [];
  const notifications =
    filter === "unread" ? allNotifications.filter((item) => !item.read) : allNotifications;
  const grouped = useMemo(() => groupNotifications(notifications), [notifications]);

  const unreadCount = data?.unread_count ?? allNotifications.filter((item) => !item.read).length;
  const alertCount = allNotifications.filter(
    (item) => item.severity === "warning" || item.severity === "critical",
  ).length;

  const handleRead = async (id: string) => {
    try {
      await markNotificationRead(id);
      await mutate();
    } catch (readError) {
      setError(readError instanceof Error ? readError.message : "Failed to mark read");
    }
  };

  const handleReadAll = async () => {
    setActing(true);
    setError(null);
    setMessage(null);
    try {
      await markAllNotificationsRead();
      await mutate();
      setMessage("All notifications marked read.");
    } catch (readAllError) {
      setError(readAllError instanceof Error ? readAllError.message : "Failed to mark all read");
    } finally {
      setActing(false);
    }
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <PageHeader
        title="Notifications"
        description="Approvals, jobs, security alerts, and workspace events in one inbox."
        actions={
          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Button
              component="a"
              href="/settings/notifications"
              size="small"
              variant="outlined"
              startIcon={<IconSettings size={16} stroke={1.75} />}
            >
              Preferences
            </Button>
            <Button
              size="small"
              variant="contained"
              startIcon={<IconCheck size={16} stroke={1.75} />}
              disabled={!unreadCount || acting}
              onClick={() => void handleReadAll()}
            >
              Mark all read
            </Button>
          </Stack>
        }
      />

      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard
            title="Unread"
            value={unreadCount}
            loading={isLoading}
            icon={<IconBell size={22} stroke={1.75} />}
            color={unreadCount > 0 ? "warning" : "success"}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard
            title="Total"
            value={allNotifications.length}
            loading={isLoading}
            icon={<IconBell size={22} stroke={1.75} />}
            color="primary"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard
            title="Warnings and critical"
            value={alertCount}
            loading={isLoading}
            icon={<IconAlertTriangle size={22} stroke={1.75} />}
            color={alertCount > 0 ? "error" : "success"}
          />
        </Grid>
      </Grid>

      <Tabs value={filter} onChange={(_, value: FilterTab) => setFilter(value)}>
        <Tab value="all" label={`All (${allNotifications.length})`} />
        <Tab value="unread" label={`Unread (${unreadCount})`} />
      </Tabs>

      {isLoading ? (
        <SkeletonList rows={3} rowHeight={96} />
      ) : notifications.length === 0 ? (
        <EmptyState
          title={filter === "unread" ? "No unread notifications" : "No notifications yet"}
          description={
            filter === "unread"
              ? "You are caught up. Switch to All to review older messages."
              : "When approvals, jobs, or alerts fire, they will appear here."
          }
          icon={<IconBell size={40} stroke={1.5} />}
          actionLabel="Notification preferences"
          onAction={() => {
            window.location.href = "/settings/notifications";
          }}
        />
      ) : (
        <Stack spacing={2}>
          {GROUP_ORDER.map((label) => {
            const items = grouped[label];
            if (!items.length) return null;
            return (
              <DashboardCard key={label} title={label} subtitle={`${items.length} notification(s)`}>
                <Stack spacing={1.5}>
                  {items.map((item) => (
                    <NotificationCard key={item.id} item={item} onRead={handleRead} />
                  ))}
                </Stack>
              </DashboardCard>
            );
          })}
        </Stack>
      )}
    </Box>
  );
}
