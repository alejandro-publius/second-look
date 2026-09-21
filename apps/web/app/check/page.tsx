import type { Metadata } from "next";
import { CheckFlow } from "@/components/CheckFlow";
import { QueueWatcher } from "@/components/QueueWatcher";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("check.title")}: ${t("app.name")}` };

export default function CheckPage() {
  return (
    <>
      <CheckFlow />
      <QueueWatcher />
    </>
  );
}
