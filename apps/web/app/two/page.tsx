import type { Metadata } from "next";
import { TwoObservers } from "@/components/TwoObservers";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("two.title")}: ${t("app.name")}` };

export default function TwoPage() {
  return <TwoObservers />;
}
