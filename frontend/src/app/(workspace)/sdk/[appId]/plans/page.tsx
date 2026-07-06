"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ceApi } from "@/lib/ce-api";

type PlanRow = {
  id: string;
  user_input: string;
  status: string;
  requires_confirmation: boolean;
  created_at?: string;
  plan?: { steps?: Array<{ entity: string; operation: string; fields?: Record<string, unknown> }> };
};

export default function SdkPlansPage() {
  const params = useParams<{ appId: string }>();
  const appId = params.appId;
  const [plans, setPlans] = useState<PlanRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!appId) return;
    ceApi(`/api/sdk/apps/${appId}/plans`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Failed to load plans");
        }
        const payload = (await response.json()) as { plans: PlanRow[] };
        setPlans(payload.plans || []);
      })
      .catch((err: Error) => setError(err.message));
  }, [appId]);

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <Link className="text-sm underline" href="/sdk">
          Back to SDK apps
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">Plan history</h1>
        <p className="mt-1 text-sm text-muted-foreground">App {appId}</p>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <section className="rounded-lg border p-4">
        <ul className="space-y-3 text-sm">
          {plans.map((plan) => (
            <li key={plan.id} className="border-b pb-3">
              <div className="font-medium">{plan.user_input}</div>
              <div className="text-xs text-muted-foreground">
                {plan.status} · {plan.created_at || "unknown time"}
                {plan.requires_confirmation ? " · confirmation required" : ""}
              </div>
              <pre className="mt-2 overflow-x-auto rounded bg-muted p-2 text-xs">
                {JSON.stringify(plan.plan?.steps || [], null, 2)}
              </pre>
            </li>
          ))}
          {!plans.length ? <li>No plans yet.</li> : null}
        </ul>
      </section>
    </div>
  );
}
