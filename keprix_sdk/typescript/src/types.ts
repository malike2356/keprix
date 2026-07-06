export interface ActionStep {
  entity: string;
  operation: string;
  fields: Record<string, unknown>;
  missing_fields?: string[];
  confirmation_required?: boolean;
  confidence?: number;
  result?: unknown;
}

export interface ActionPlan {
  user_input: string;
  session_id?: string | null;
  steps: ActionStep[];
  requires_confirmation?: boolean;
  confirmation_prompt?: string;
  plan_id?: string | null;
}

export interface ExecutionResult {
  success: boolean;
  steps: ActionStep[];
}
