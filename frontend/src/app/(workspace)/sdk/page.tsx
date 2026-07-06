"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ceApi } from "@/lib/ce-api";

type SdkApp = {
  id: string;
  name: string;
  version: string;
  webhook_url?: string | null;
  last_seen_at?: string | null;
  entity_count?: number;
};

export default function SdkAdminPage() {
  const [apps, setApps] = useState<SdkApp[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");

  const load = () => {
    ceApi("/api/sdk/apps")
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Failed to load SDK apps");
        }
        const payload = (await response.json()) as { apps: SdkApp[] };
        setApps(payload.apps || []);
      })
      .catch((err: Error) => setError(err.message));
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">SDK App Manager</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Registered App Foundation SDK apps, schemas, and plan history.
        </p>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <section className="rounded-lg border p-4">
        <h2 className="font-medium">Registered apps</h2>
        <ul className="mt-3 space-y-2 text-sm">
          {apps.map((app) => (
            <li key={app.id} className="flex flex-wrap items-center justify-between gap-2 border-b pb-2">
              <div>
                <div className="font-medium">{app.name}</div>
                <div className="text-xs text-muted-foreground">
                  {app.id} · v{app.version} · {app.entity_count ?? 0} entities
                </div>
                {app.last_seen_at ? (
                  <div className="text-xs text-muted-foreground">Last seen: {app.last_seen_at}</div>
                ) : null}
              </div>
              <Link className="text-sm underline" href={`/sdk/${app.id}/plans`}>
                View plans
              </Link>
            </li>
          ))}
          {!apps.length ? <li>No SDK apps registered yet.</li> : null}
        </ul>
      </section>

      <section className="rounded-lg border p-4">
        <h2 className="font-medium">Register via SDK</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Apps register themselves with <code>POST /api/sdk/apps/register</code> using an API key.
          Use the Python or TypeScript SDK from your application process.
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <input
            className="rounded border px-3 py-2 text-sm"
            placeholder="App name (documentation only)"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            className="rounded border px-3 py-2 text-sm"
            placeholder="Webhook URL (optional)"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
          />
        </div>
      </section>
    </div>
  );
}
