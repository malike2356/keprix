"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

export type ResourceAclEntry = {
  resource_id: string;
  resource_type: string;
  principal: string;
  role: string;
};

type Props = {
  resourceId?: string;
  entries?: ResourceAclEntry[];
};

/**
 * Minimal resource ACL panel. No backend route or importer currently exists
 * for per-resource access control lists; this renders a safe, valid module
 * so it can be wired up to a route once that surface ships.
 */
export default function ResourceAclPanel({ resourceId, entries = [] }: Props) {
  return (
    <Box sx={{ py: 2 }}>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        Resource access
      </Typography>
      {entries.length === 0 ? (
        <Alert severity="info">
          {resourceId
            ? `No access entries recorded for ${resourceId} yet.`
            : "No access entries recorded yet."}
        </Alert>
      ) : (
        <Box sx={{ display: "grid", gap: 1 }}>
          {entries.map((entry) => (
            <Box
              key={`${entry.resource_id}-${entry.principal}`}
              sx={{ display: "flex", justifyContent: "space-between", gap: 1 }}
            >
              <Typography variant="body2">{entry.principal}</Typography>
              <Typography variant="body2" color="text.secondary">
                {entry.role}
              </Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}
