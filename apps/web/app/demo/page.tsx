import type { Metadata } from "next";
import { DemoFlow } from "@/components/DemoFlow";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("demo.title")}: ${t("app.name")}` };

// ?script=1 is read here so the page stays static otherwise. Next makes it dynamic when the
// search params are awaited, which is fine for judge mode.
export default async function DemoPage({ searchParams }: { searchParams: Promise<{ script?: string | string[] }> }) {
  const params = await searchParams;
  const scripted = params.script === "1";
  return <DemoFlow scripted={scripted} />;
}
