import { ceApi, getApiBaseUrl, parseApiErrorMessage } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (payload && typeof payload === "object" && (payload as { detail?: unknown }).detail) {
      const detail = (payload as { detail: unknown }).detail;
      if (typeof detail === "object" && detail && "message" in (detail as object)) {
        throw new Error(String((detail as { message: string }).message));
      }
      if (typeof detail === "string") throw new Error(detail);
    }
    throw new Error(parseApiErrorMessage(payload, fallback));
  }
  return payload as T;
}

export type VicalStatus = {
  ok: boolean;
  enabled: boolean;
  event_type_count: number;
  default_slug: string;
  public_slug?: string | null;
  public_book_path?: string;
  docs?: string;
};

export type VicalEventType = {
  id: string;
  slug: string;
  name: string;
  duration_minutes: number;
  requires_approval: boolean;
  requires_deposit: boolean;
  deposit_minor?: number | null;
  deposit_currency?: string | null;
  intake_pool_id?: string | null;
  active: boolean;
  location_mode?: string;
};

export type VicalBooking = {
  id: string;
  event_type_id: string;
  guest_name: string;
  guest_email: string;
  starts_at: string;
  ends_at: string;
  status: string;
  guest_token: string;
  workspace_event_id?: string | null;
  meeting_url?: string | null;
  intake_answers?: Record<string, unknown>;
  notes?: string | null;
  contact_id?: string | null;
  checkout?: {
    checkout_url?: string;
    session_id?: string;
    amount_minor?: number;
    currency?: string;
  };
  event_type?: { id: string; slug: string; name: string; duration_minutes: number };
};

export type VicalSlot = {
  start_at: string;
  end_at: string;
};

export type VicalHostProfile = {
  user_id: string;
  public_slug?: string;
  display_name?: string;
  webhook_url?: string | null;
  meeting_url_template?: string | null;
};

export type PublicHostPayload = {
  host: { public_slug?: string; display_name: string; user_id: string };
  event_types: VicalEventType[];
};

export type IntakePoolPublic = {
  required: boolean;
  pool: {
    id: string;
    name?: string;
    questions: Array<{
      id: string;
      label: string;
      type: string;
      required: boolean;
      options: Array<string | { value: string; label?: string }>;
    }>;
  } | null;
  event_type_id?: string;
};

export async function fetchVicalStatus(): Promise<VicalStatus> {
  return parseJson(await ceApi("/api/vical/status"), "Could not load viCal status");
}

export async function seedVical(): Promise<{ ok: boolean; public_book_path?: string }> {
  const result = await parseJson<{ ok: boolean; host_profile?: VicalHostProfile }>(
    await ceApi("/api/vical/seed", { method: "POST", body: "{}" }),
    "Could not seed viCal",
  );
  const slug = result.host_profile?.public_slug;
  return { ok: result.ok, public_book_path: slug ? `/book/${slug}` : undefined };
}

export async function fetchHostProfile(): Promise<{ profile: VicalHostProfile; public_book_path: string }> {
  return parseJson(await ceApi("/api/vical/host-profile"), "Could not load host profile");
}

export async function updateHostProfile(body: Partial<VicalHostProfile>): Promise<{
  profile: VicalHostProfile;
  public_book_path: string;
}> {
  return parseJson(
    await ceApi("/api/vical/host-profile", { method: "PUT", body: JSON.stringify(body) }),
    "Could not update host profile",
  );
}

export async function fetchEventTypes(): Promise<VicalEventType[]> {
  const data = await parseJson<{ items: VicalEventType[] }>(
    await ceApi("/api/vical/event-types"),
    "Could not load event types",
  );
  return data.items;
}

export async function createEventType(body: Partial<VicalEventType> & { slug: string; name: string }): Promise<VicalEventType> {
  return parseJson(
    await ceApi("/api/vical/event-types", { method: "POST", body: JSON.stringify(body) }),
    "Could not create event type",
  );
}

export async function patchEventType(id: string, body: Partial<VicalEventType>): Promise<VicalEventType> {
  return parseJson(
    await ceApi(`/api/vical/event-types/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
    "Could not update event type",
  );
}

export async function fetchAvailabilityRules(): Promise<Array<Record<string, unknown>>> {
  const data = await parseJson<{ items: Array<Record<string, unknown>> }>(
    await ceApi("/api/vical/availability-rules"),
    "Could not load availability",
  );
  return data.items;
}

export async function createAvailabilityRule(body: {
  day_of_week: number;
  start_time: string;
  end_time: string;
  timezone?: string;
}): Promise<Record<string, unknown>> {
  return parseJson(
    await ceApi("/api/vical/availability-rules", { method: "POST", body: JSON.stringify(body) }),
    "Could not create availability rule",
  );
}

export async function fetchBlackouts(): Promise<Array<Record<string, unknown>>> {
  const data = await parseJson<{ items: Array<Record<string, unknown>> }>(
    await ceApi("/api/vical/blackouts"),
    "Could not load blackouts",
  );
  return data.items;
}

export async function createBlackout(body: {
  starts_on: string;
  ends_on: string;
  reason?: string;
}): Promise<Record<string, unknown>> {
  return parseJson(
    await ceApi("/api/vical/blackouts", { method: "POST", body: JSON.stringify(body) }),
    "Could not create blackout",
  );
}

export async function fetchBookings(): Promise<VicalBooking[]> {
  const data = await parseJson<{ items: VicalBooking[] }>(
    await ceApi("/api/vical/bookings"),
    "Could not load bookings",
  );
  return data.items;
}

export async function approveBooking(id: string): Promise<VicalBooking> {
  return parseJson(
    await ceApi(`/api/vical/bookings/${encodeURIComponent(id)}/approve`, { method: "POST", body: "{}" }),
    "Could not approve booking",
  );
}

export async function rejectBooking(id: string): Promise<VicalBooking> {
  return parseJson(
    await ceApi(`/api/vical/bookings/${encodeURIComponent(id)}/reject`, { method: "POST", body: "{}" }),
    "Could not reject booking",
  );
}

export async function cancelBooking(id: string): Promise<VicalBooking> {
  return parseJson(
    await ceApi(`/api/vical/bookings/${encodeURIComponent(id)}/cancel`, { method: "POST", body: "{}" }),
    "Could not cancel booking",
  );
}

export async function fetchIntakePools(): Promise<Array<Record<string, unknown>>> {
  const data = await parseJson<{ items: Array<Record<string, unknown>> }>(
    await ceApi("/api/vical/intake-pools"),
    "Could not load intake pools",
  );
  return data.items;
}

export async function createIntakePool(body: {
  name: string;
  questions: Array<Record<string, unknown>>;
}): Promise<Record<string, unknown>> {
  return parseJson(
    await ceApi("/api/vical/intake-pools", { method: "POST", body: JSON.stringify(body) }),
    "Could not create intake pool",
  );
}

export async function createDepositCheckout(bookingId: string): Promise<Record<string, unknown>> {
  return parseJson(
    await ceApi(`/api/vical/deposits/${encodeURIComponent(bookingId)}/checkout`, {
      method: "POST",
      body: "{}",
    }),
    "Could not create deposit checkout",
  );
}

// Public (guest) helpers; may run without workspace login.

export async function fetchPublicHost(slug: string): Promise<PublicHostPayload> {
  return parseJson(
    await ceApi(`/api/vical/public/hosts/${encodeURIComponent(slug)}`),
    "Host not found",
  );
}

export async function fetchPublicSlots(
  slug: string,
  opts?: { eventTypeId?: string; eventSlug?: string; count?: number },
): Promise<VicalSlot[]> {
  const params = new URLSearchParams();
  if (opts?.eventTypeId) params.set("event_type_id", opts.eventTypeId);
  if (opts?.eventSlug) params.set("slug", opts.eventSlug);
  if (opts?.count) params.set("count", String(opts.count));
  const qs = params.toString();
  const data = await parseJson<{ items: VicalSlot[] }>(
    await ceApi(`/api/vical/public/hosts/${encodeURIComponent(slug)}/slots${qs ? `?${qs}` : ""}`),
    "Could not load slots",
  );
  return data.items;
}

export async function fetchPublicIntake(
  slug: string,
  opts?: { eventTypeId?: string; eventSlug?: string },
): Promise<IntakePoolPublic> {
  const params = new URLSearchParams();
  if (opts?.eventTypeId) params.set("event_type_id", opts.eventTypeId);
  if (opts?.eventSlug) params.set("slug", opts.eventSlug);
  const qs = params.toString();
  return parseJson(
    await ceApi(`/api/vical/public/hosts/${encodeURIComponent(slug)}/intake${qs ? `?${qs}` : ""}`),
    "Could not load intake",
  );
}

export async function validatePublicIntake(
  slug: string,
  body: { event_type_slug?: string; event_type_id?: string; answers: Record<string, unknown> },
): Promise<{ ok: boolean; answers: Record<string, unknown> }> {
  return parseJson(
    await ceApi(`/api/vical/public/hosts/${encodeURIComponent(slug)}/intake/validate`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Intake validation failed",
  );
}

export async function createPublicBooking(
  slug: string,
  body: {
    event_type_slug?: string;
    event_type_id?: string;
    guest_name: string;
    guest_email: string;
    starts_at: string;
    ends_at?: string;
    notes?: string;
    intake_answers?: Record<string, unknown>;
  },
): Promise<VicalBooking> {
  return parseJson(
    await ceApi(`/api/vical/public/hosts/${encodeURIComponent(slug)}/bookings`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
    "Could not create booking",
  );
}

export async function cancelByGuestToken(guestToken: string): Promise<VicalBooking> {
  return parseJson(
    await ceApi("/api/vical/public/cancel", {
      method: "POST",
      body: JSON.stringify({ guest_token: guestToken }),
    }),
    "Could not cancel booking",
  );
}

export async function rescheduleByGuestToken(
  guestToken: string,
  startsAt: string,
  endsAt?: string,
): Promise<VicalBooking> {
  return parseJson(
    await ceApi("/api/vical/public/reschedule", {
      method: "POST",
      body: JSON.stringify({ guest_token: guestToken, starts_at: startsAt, ends_at: endsAt }),
    }),
    "Could not reschedule booking",
  );
}

export async function fetchBookingByToken(guestToken: string): Promise<VicalBooking> {
  return parseJson(
    await ceApi(`/api/vical/public/bookings/by-token?guest_token=${encodeURIComponent(guestToken)}`),
    "Booking not found",
  );
}

export function publicIcsUrl(guestToken: string): string {
  return `${getApiBaseUrl()}/api/vical/public/bookings/by-token/ics?guest_token=${encodeURIComponent(guestToken)}`;
}
