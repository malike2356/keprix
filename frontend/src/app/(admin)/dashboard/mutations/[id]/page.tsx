import { redirect } from "next/navigation";

type LegacyMutationDetailProps = {
  params: Promise<{ id: string }>;
};

export default async function LegacyMutationDetailRedirect({ params }: LegacyMutationDetailProps) {
  const { id } = await params;
  redirect(`/dashboard/mutation/${id}`);
}
