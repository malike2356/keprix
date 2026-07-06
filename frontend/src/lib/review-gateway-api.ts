import { ceApi } from "@/lib/ce-api";

export type ReviewRequest = {
  id: string;
  title: string;
  reviewer_name: string;
  reviewer_email: string;
  status: string;
  created_at: string;
  expires_at: string;
  decision?: { action: string; reviewer_note: string };
};

export async function fetchReviewRequests(): Promise<{ requests: ReviewRequest[] }> {
  const response = await ceApi("/api/review-gateway/requests");
  if (!response.ok) throw new Error("Failed to load review requests");
  return response.json();
}

export async function createReviewRequest(body: Record<string, unknown>): Promise<{ id: string; review_url: string }> {
  const response = await ceApi("/api/review-gateway/requests", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("Failed to create review request");
  return response.json();
}
