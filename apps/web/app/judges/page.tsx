import type { Metadata } from "next";
import Link from "next/link";
import { FocusHeading } from "@/components/FocusHeading";
import { Row } from "@/components/ui/Row";
import { content } from "@/lib/content";
import { t } from "@/lib/t";

export const metadata: Metadata = { title: `${t("judges.title")}: ${t("app.name")}` };

// The repository is private until Sep 30 (hard rule 15). These links open on that day, and each
// door's line says so.
const REPO = "https://github.com/alejandro-publius/second-look";

// No stored record answers to a sample id on the live site, so the sample record is the one a
// video walk makes on the phone, with View as FHIR at its end. The same walk's end has the city
// view of the creek it fed, which is the full city page; the live creek's own page stays empty
// until a real check arrives, and the city door's line says so (CRITIC_02 D05).
const walk = content.walks[0];
const walkHref = `/walk/${walk?.id ?? ""}`;
const clip = { seconds: walk?.clip.seconds ?? "" };

// The judges' front door. The participant's front door, /, carries the wordmark and About and
// nothing else, so a person taking the test is never one tap from the answer key or the code.
// Judge mode leads because it stores nothing. The real test is the study, so it comes second and
// says so, and a judge's first tap never adds a session to the data. Every door has one line under
// it: what it shows and about how long it takes (CRITIC_02 D03 and D11).
const DOORS: { href: string; label: string; note: string; params?: Record<string, string | number> }[] = [
  { href: "/demo", label: "judges.demo", note: "judges.demo_note" },
  { href: "/t?src=other", label: "judges.take_test", note: "judges.take_test_note" },
  { href: "/check", label: "judges.check", note: "judges.check_note" },
  { href: "/walk", label: "judges.walks", note: "judges.walks_note", params: clip },
  { href: walkHref, label: "judges.record", note: "judges.record_note", params: clip },
  { href: walkHref, label: "nav.city", note: "judges.city_note", params: { button: t("walk.city_link") } },
  { href: "/two", label: "judges.two", note: "judges.two_note" },
  { href: "/how-we-know", label: "judges.how", note: "judges.how_note" },
  { href: `${REPO}#for-judges`, label: "judges.readme", note: "judges.readme_note" },
  { href: `${REPO}/blob/main/docs/REPORT.pdf`, label: "judges.report", note: "judges.report_note" },
  { href: `${REPO}/blob/main/docs/MODEL_CARD.md`, label: "judges.model_card", note: "judges.model_card_note" },
  { href: REPO, label: "judges.repo", note: "judges.repo_note" },
  { href: "/verify", label: "judges.verify", note: "judges.verify_note" },
  { href: "/credits", label: "nav.credits", note: "judges.credits_note" },
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
          <Row
            key={d.label}
            label={
              d.href.startsWith("https://") ? (
                <a className="row-link" href={d.href} rel="noreferrer">
                  {t(d.label, d.params)}
                </a>
              ) : (
                <Link className="row-link" href={d.href}>
                  {t(d.label, d.params)}
                </Link>
              )
            }
            value={t(d.note, d.params)}
          />
        ))}
      </nav>
    </div>
  );
}
