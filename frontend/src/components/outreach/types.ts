export type PipelineStatus =
  | "new"
  | "enrolled"
  | "contacted"
  | "replied"
  | "interested"
  | "booking"
  | "booked"
  | "won"
  | "lost"
  | "not_now"
  | "unsubscribed"
  | "follow_up"
  | "attended"
  | "ghosted"
  | "proposal_sent";

export type OutreachLead = {
  id: string;
  name: string;
  email?: string | null;
  phone?: string | null;
  company?: string | null;
  source?: string | null;
  source_url?: string | null;
  sourceUrl?: string | null;
  campaign_id?: string | null;
  campaignId?: string | null;
  status: string;
  owner?: string | null;
  notes?: string | null;
  tags?: string[];
  reply_state?: string | null;
  replyState?: string | null;
  booking_state?: string | null;
  bookingState?: string | null;
  next_action_at?: string | null;
  nextActionAt?: string | null;
  created_at?: string | null;
  createdAt?: string | null;
  updated_at?: string | null;
  updatedAt?: string | null;
  timeline?: Array<{
    id?: string;
    at?: string;
    kind?: string;
    message?: string;
    from_status?: string;
    to_status?: string;
  }>;
};

export type OutreachCampaign = {
  id: string;
  name: string;
  objective?: string | null;
  target_audience?: string | null;
  status?: string | null;
  active?: boolean;
  daily_cap?: number | null;
  timezone?: string | null;
  business_hours_start?: string | null;
  business_hours_end?: string | null;
  require_approval?: boolean | null;
  default_sequence_id?: string | null;
  default_booking_link?: string | null;
  source_type?: string | null;
  updated_at?: string | null;
};

export type OutreachSequenceStep = {
  id?: string;
  order?: number;
  label?: string;
  channel?: string;
  subject?: string;
  body?: string;
  delay_hours?: number;
  delayHours?: number;
  cta?: string;
  link?: string;
};

export type OutreachSequence = {
  id: string;
  name: string;
  description?: string | null;
  channel_default?: string | null;
  steps: OutreachSequenceStep[];
  stop_on_reply?: boolean;
  stop_on_booking?: boolean;
  stop_on_unsubscribe?: boolean;
  stopOnReply?: boolean;
  stopOnBooking?: boolean;
  stopOnUnsubscribe?: boolean;
  updated_at?: string | null;
};

export type OutreachReply = {
  id: string;
  lead_id?: string | null;
  leadId?: string | null;
  from_email?: string | null;
  fromEmail?: string | null;
  subject?: string | null;
  body?: string | null;
  body_preview?: string | null;
  bodyPreview?: string | null;
  classification?: string | null;
  confidence?: number | null;
  status?: string | null;
  resolved?: boolean | null;
  note?: string | null;
  suggested_reply?: string | null;
  suggestedReply?: string | null;
  updated_at?: string | null;
  updatedAt?: string | null;
};

export type OutreachBooking = {
  id: string;
  lead_id?: string | null;
  leadId?: string | null;
  status: string;
  starts_at?: string | null;
  startsAt?: string | null;
  ends_at?: string | null;
  endsAt?: string | null;
  attendee_name?: string | null;
  attendee_email?: string | null;
  join_link?: string | null;
  notes?: string | null;
};

export type OutreachList = {
  id: string;
  name: string;
  description?: string | null;
  lead_ids?: string[];
  leadIds?: string[];
  tags?: string[];
  updated_at?: string | null;
};

export type OutreachApproval = {
  id: string;
  recipient?: string | null;
  to?: string | null;
  subject?: string | null;
  draft_body?: string | null;
  draftBody?: string | null;
  body?: string | null;
  status?: string | null;
  category?: string | null;
  requested_at?: string | null;
  requestedAt?: string | null;
  created_at?: string | null;
};

export type OutreachControlState = {
  paused: boolean;
  reason?: string | null;
  updated_at?: string | null;
  updatedAt?: string | null;
  updated_by?: string | null;
};

export type OutreachOverview = {
  summary: Record<string, number>;
  pendingApprovals: number;
  activeEnrollments: number;
  openReplyReviews?: number;
  upcomingBookings?: number;
  scheduledReminders?: number;
  defaults?: {
    campaign?: { id: string; name: string } | null;
    sequence?: { id: string; name: string; steps?: unknown[] } | null;
  };
  pipeline?: Record<string, number>;
};

export const PIPELINE_LABELS: Record<PipelineStatus, string> = {
  new: "New",
  enrolled: "Enrolled",
  contacted: "Contacted",
  replied: "Replied",
  interested: "Interested",
  booking: "Booking",
  booked: "Booked",
  won: "Won",
  lost: "Lost",
  not_now: "Not now",
  unsubscribed: "Unsubscribed",
  follow_up: "Follow-up",
  attended: "Attended",
  ghosted: "Ghosted",
  proposal_sent: "Proposal sent",
};

export const PIPELINE_STAGES = Object.keys(PIPELINE_LABELS) as PipelineStatus[];

export function pipelineLabel(status: string | null | undefined): string {
  if (!status) return "Unknown";
  return PIPELINE_LABELS[status as PipelineStatus] ?? status.replace(/_/g, " ");
}

export function leadIdsOf(list: OutreachList): string[] {
  return list.lead_ids ?? list.leadIds ?? [];
}
