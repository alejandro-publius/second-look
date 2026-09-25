import type { Metadata } from "next";
import { Part2Flow } from "@/components/Part2Flow";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("part2.title")}: ${t("app.name")}` };

export default function Part2Page() {
  return <Part2Flow />;
}
