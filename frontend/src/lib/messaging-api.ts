import { ceApi } from "@/lib/ce-api";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || fallback);
  }
  return response.json();
}

export type RoomConfig = {
  room_id: string;
  channel_type: string;
  workspace_id: string;
  unmentioned_inbound: "normal" | "room_event";
  visible_replies: "auto" | "message_tool";
  history_limit: number;
  mention_gating: boolean;
  always_on: boolean;
  supports_always_on?: boolean;
};

export async function fetchRooms(workspaceId = "default") {
  return parseJson<{ rooms: RoomConfig[]; count: number }>(
    await ceApi(`/api/rooms?workspace_id=${encodeURIComponent(workspaceId)}`),
    "rooms",
  );
}

export async function fetchRoomConfig(roomId: string, workspaceId = "default", channelType = "whatsapp") {
  const query = new URLSearchParams({ workspace_id: workspaceId, channel_type: channelType });
  return parseJson<RoomConfig>(
    await ceApi(`/api/rooms/${encodeURIComponent(roomId)}/config?${query.toString()}`),
    "room config",
  );
}

export async function patchRoomConfig(roomId: string, body: Partial<RoomConfig>, workspaceId = "default") {
  const query = new URLSearchParams({ workspace_id: workspaceId });
  return parseJson<RoomConfig>(
    await ceApi(`/api/rooms/${encodeURIComponent(roomId)}/config?${query.toString()}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "room config patch",
  );
}

export async function enableAmbientMode(roomId: string, workspaceId = "default", channelType = "whatsapp") {
  return parseJson<RoomConfig>(
    await ceApi(`/api/rooms/${encodeURIComponent(roomId)}/config/ambient`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: workspaceId, channel_type: channelType }),
    }),
    "ambient enable",
  );
}
