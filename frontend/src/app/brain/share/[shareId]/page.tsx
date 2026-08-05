import BrainSharedGraphPage from "@/components/brain/BrainSharedGraphPage";

type Props = {
  params: Promise<{ shareId: string }>;
};

export default async function SharedBrainPage({ params }: Props) {
  const { shareId } = await params;
  return <BrainSharedGraphPage shareId={shareId} />;
}
