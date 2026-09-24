import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { WalkFlow } from "@/components/WalkFlow";
import { content, walkById } from "@/lib/content";
import { t } from "@/lib/t";

// /walk/<id>. The walks are known at build time (content/walks.yaml), so each is a static page.
export function generateStaticParams() {
  return (content.walks ?? []).map((w) => ({ id: w.id }));
}

export const dynamicParams = false;

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const walk = walkById(id);
  return { title: `${walk ? walk.creek_name : t("walk.list_title")}: ${t("app.name")}` };
}

export default async function WalkPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const walk = walkById(id);
  if (!walk) notFound();
  return <WalkFlow walk={walk} />;
}
