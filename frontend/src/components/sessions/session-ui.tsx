"use client";

/**
 * Portable "Where you're logged in" React panel.
 * Products wire fetch helpers; this component stays UI-only.
 */
import React, { useCallback, useEffect, useState } from 'react';


export type SessionUiRow = {
  sessionId: string;
  deviceLabel: string;
  location?: string | null;
  ipMasked?: string | null;
  lastActiveAt?: string | null;
  createdAt?: string | null;
  isCurrent?: boolean;
};

export type SessionUiApi = {
  list: () => Promise<SessionUiRow[]>;
  revokeOne: (sessionId: string) => Promise<void>;
  revokeAll: () => Promise<void>;
};

export type SessionManagementPanelProps = {
  api: SessionUiApi;
  newLoginBanner?: string | null;
  onDismissBanner?: () => void;
  title?: string;
};

export function SessionManagementPanel(props: SessionManagementPanelProps): React.ReactElement {
  const { api, newLoginBanner, onDismissBanner, title = "Where you're logged in" } = props;
  const [rows, setRows] = useState<SessionUiRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      setRows(await api.list());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [api]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function onRevoke(sessionId: string): Promise<void> {
    setBusy(true);
    try {
      await api.revokeOne(sessionId);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onRevokeAll(): Promise<void> {
    setBusy(true);
    try {
      await api.revokeAll();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label={title} style={{ fontFamily: 'system-ui, sans-serif', maxWidth: 640 }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <h2 style={{ margin: 0, fontSize: '1.15rem' }}>{title}</h2>
        <button type="button" disabled={busy} onClick={() => void onRevokeAll()}>
          Log out everywhere
        </button>
      </header>
      {newLoginBanner ? (
        <p role="status" style={{ marginTop: 12, padding: 10, background: '#f5f5f5' }}>
          {newLoginBanner}{' '}
          {onDismissBanner ? (
            <button type="button" onClick={onDismissBanner}>
              Dismiss
            </button>
          ) : null}
        </p>
      ) : null}
      {error ? (
        <p role="alert" style={{ color: '#b00020' }}>
          {error}
        </p>
      ) : null}
      <ul style={{ listStyle: 'none', padding: 0, marginTop: 16 }}>
        {rows.map((row) => (
          <li
            key={row.sessionId}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              gap: 12,
              padding: '10px 0',
              borderBottom: '1px solid #e5e5e5',
            }}
          >
            <div>
              <strong>{row.deviceLabel}</strong>
              {row.isCurrent ? <span> (this device)</span> : null}
              <div style={{ fontSize: '0.85rem', opacity: 0.8 }}>
                {[row.location, row.ipMasked, row.lastActiveAt ? `Last active ${row.lastActiveAt}` : null]
                  .filter(Boolean)
                  .join(' · ')}
              </div>
            </div>
            {!row.isCurrent ? (
              <button type="button" disabled={busy} onClick={() => void onRevoke(row.sessionId)}>
                Log out this device
              </button>
            ) : null}
          </li>
        ))}
      </ul>
      {rows.length === 0 && !error ? <p>No active sessions.</p> : null}
    </section>
  );
}

export default SessionManagementPanel;
