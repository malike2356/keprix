"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Link from "@mui/material/Link";
import Skeleton from "@mui/material/Skeleton";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import { fetchTasks, type WorkspaceTask } from "@/lib/workspace-api";

const STATUS_COLORS: Record<string, string> = {
  todo: "#9e9e9e",
  in_progress: "#1976d2",
  done: "#2e7d32",
};

function TaskRow({ task }: { task: WorkspaceTask }) {
  const color = STATUS_COLORS[task.status] ?? "#9e9e9e";
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "flex-start",
        gap: 1.5,
        py: 1,
        "&:not(:last-child)": { borderBottom: "1px solid", borderColor: "divider" },
      }}
    >
      <Box
        sx={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          bgcolor: color,
          mt: "5px",
          flexShrink: 0,
        }}
      />
      <Typography
        variant="body2"
        sx={{
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          flex: 1,
        }}
      >
        {task.title}
      </Typography>
    </Box>
  );
}

export default function TasksWidget() {
  const { data: tasks, isLoading } = useSWR<WorkspaceTask[]>(
    "home-tasks",
    () => fetchTasks(),
    { revalidateOnFocus: false },
  );

  const activeTasks = (tasks ?? []).filter((t) => t.status !== "done").slice(0, 5);

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1.5 }}>
        <Typography variant="subtitle2" fontWeight={600}>
          Tasks
        </Typography>
        <Link
          component="a"
          href="/tasks"
          variant="caption"
          color="text.secondary"
          underline="hover"
        >
          See all
        </Link>
      </Box>

      <Card variant="outlined">
        <CardContent sx={{ px: 2, py: 1, "&:last-child": { pb: 1 } }}>
          {isLoading ? (
            <>
              <Skeleton variant="text" sx={{ my: 1 }} />
              <Skeleton variant="text" sx={{ my: 1 }} />
              <Skeleton variant="text" sx={{ my: 1 }} />
            </>
          ) : activeTasks.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ py: 1 }}>
              No active tasks.
            </Typography>
          ) : (
            activeTasks.map((t) => <TaskRow key={t.id} task={t} />)
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
