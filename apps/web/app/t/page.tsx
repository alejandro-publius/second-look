import type { Metadata } from "next";
import { TestFlow } from "@/components/TestFlow";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("consent.title")}: ${t("app.name")}` };

export default function TestPage() {
  return <TestFlow />;
}
