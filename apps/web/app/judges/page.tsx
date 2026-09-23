import type { Metadata } from "next";
import Link from "next/link";
import { FocusHeading } from "@/components/FocusHeading";
import { Row } from "@/components/ui/Row";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("judges.title")}: ${t("app.name")}` };

// The judges' front door. The participant's front door, /, carries the wordmark and About and
// nothing else, so a person taking the test is never one tap from the answer key or the code.
// Judge mode leads because it stores nothing. The real test is the study, so it comes second and
// says so, and a judge's first tap never adds a session to the data.
const DOORS: { href: string; label: string; note?: string }[] = [
  { href: "/demo", label: "judges.demo" },
  { href: "/t?src=other", label: "judges.take_test", note: "judges.take_test_note" },
  { href: "/check", label: "judges.check" },
  { href: "/walk", label: "judges.walks" },
  { href: "/spot?id=example", label: "judges.record" },
  { href: "/two", label: "judges.two" },
  { href: "/city?creek=strawberry-creek", label: "nav.city" },
  { href: "/how-we-know", label: "judges.how" },
  { href: "/credits", label: "nav.credits" },
];

export default function JudgesPage() {
  return (
    <div className="stack">
      <FocusHeading>{t("judges.title")}</FocusHeading>
      {/* The point of the product comes first, in body size and ink: a judge with two minutes
          reads the heading, the first paragraph and the first link. */}
      <p>{t("app.one_sentence")}</p>
      <p>{t("judges.intro")}</p>
      <nav className="card" aria-label={t("judges.title")}>
        {DOORS.map((d) => (
          <Row key={d.href} label={<Link href={d.href}>{t(d.label)}</Link>} value={d.note ? t(d.note) : undefined} />
        ))}
      </nav>
    </div>
  );
}
