"use client";

import Alert from "@mui/material/Alert";
import * as React from "react";
import { acquireCrmLock, releaseCrmLock } from "@/lib/crm-api";
import { CRM_WORKSPACE } from "@/components/crm/types";

type Props = {
  entityType: "lead" | "contact" | "deal" | "account";
  entityId: string;
};

/** Soft lock while a detail page is open; warn if another operator holds the lock. */
export default function CrmSoftLockBanner({ entityType, entityId }: Props) {
  const [warning, setWarning] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await acquireCrmLock(
          { entity_type: entityType, entity_id: entityId, ttl_seconds: 180 },
          CRM_WORKSPACE,
        );
        if (cancelled) return;
        if (res.conflict) {
          setWarning(String(res.warning || "Record is locked by another operator"));
        } else {
          setWarning(null);
        }
      } catch {
        if (!cancelled) setWarning(null);
      }
    })();
    return () => {
      cancelled = true;
      void releaseCrmLock(entityType, entityId, CRM_WORKSPACE).catch(() => undefined);
    };
  }, [entityType, entityId]);

  if (!warning) return null;
  return (
    <Alert severity="warning" sx={{ mb: 2 }}>
      {warning}. Save carefully; concurrent edits may overwrite each other.
    </Alert>
  );
}
