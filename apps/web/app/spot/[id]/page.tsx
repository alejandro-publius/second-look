import type { Metadata } from "next";
import { SpotRecord } from "@/components/SpotRecord";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("spot.title")}: ${t("app.name")}` };

export default async function SpotPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SpotRecord spotId={id} />;
}
