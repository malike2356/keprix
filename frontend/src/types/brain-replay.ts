export type ReplayMessage = {
  index: number;
  role: "user" | "agent";
  content: string;
  timestamp: string;
  activations_before: string[];
  activations_during: string[];
};

export type ReplayActivation = {
  step: number;
  node_kind: string;
  node_id: string;
  node_label: string;
  relation: string;
  confidence: number | null;
  activated_at: string;
};

export type SessionReplayData = {
  session_id: string;
  session_title: string;
  session_date: string;
  messages: ReplayMessage[];
  activations: ReplayActivation[];
  activation_count: number;
  has_brain_activity: boolean;
};

export type BrainSessionSummary = {
  session_id: string;
  title: string;
  session_date: string;
  activation_count: number;
};
