import type { Metadata } from "next";
import { QuickCheck } from "@/components/QuickCheck";
import { QueueWatcher } from "@/components/QueueWatcher";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("quick.title")}: ${t("app.name")}` };

export default async function QuickPage({ params }: { params: Promise<{ spot: string }> }) {
  const { spot } = await params;
  return (
    <>
      <QuickCheck spotId={spot} />
      <QueueWatcher />
    </>
  );
}
