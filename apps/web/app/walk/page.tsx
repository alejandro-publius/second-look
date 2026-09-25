import type { Metadata } from "next";
import Link from "next/link";
import { FocusHeading } from "@/components/FocusHeading";
import { Photo } from "@/components/Photo";
import { content } from "@/lib/content";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("walk.list_title")}: ${t("app.name")}` };

// "Check a creek from your desk": the four walks, one per country. The creek's name names each
// link, so its poster is decoration and has an empty alt text (CRITIC_09 Q04).
export default function WalksPage() {
  const walks = content.walks ?? [];
  return (
    <div className="stack">
      <FocusHeading>{t("walk.list_title")}</FocusHeading>
      <p>{t("walk.list_intro")}</p>
      {walks.length === 0 ? <p className="muted">{t("walk.none")}</p> : null}
      {walks.map((w) => (
        <Link key={w.id} href={`/walk/${w.id}`} className="card stack">
          <Photo id={w.poster_photo_id} alt="" />
          <span>{w.creek_name}</span>
        </Link>
      ))}
    </div>
  );
}
