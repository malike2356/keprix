import { redirect } from "next/navigation";

export default async function SessionDetailAliasPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  redirect(`/chat/${sessionId}`);
}
