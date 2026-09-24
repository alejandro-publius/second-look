import type { Metadata } from "next";
import { t } from "@/lib/t";

// The page is a client component, which cannot name itself, so its layout gives it a title of its
// own (WCAG 2.2 SC 2.4.2, REVIEW_03 R39).
export const metadata: Metadata = { title: `${t("quick.title")}: ${t("app.name")}` };

export default function QuickLayout({ children }: { children: React.ReactNode }) {
  return children;
}
