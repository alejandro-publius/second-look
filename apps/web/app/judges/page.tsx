import type { Metadata } from "next";
import Link from "next/link";
import { FocusHeading } from "@/components/FocusHeading";
import { JudgesAssistDoor } from "@/components/JudgesAssistDoor";
import { Row } from "@/components/ui/Row";
import { content } from "@/lib/content";
import { t } from "@/lib/t";
import { auditEntries, otsStatus } from "@/lib/verify-data";
import { logStampDay } from "@/lib/verify-text";

export const metadata: Metadata = { title: `${t("judges.title")}: ${t("app.name")}` };

// The repository is private until Oct 3 (hard rule 15; the deadline moved, UPDATE_33) and public
// from that day. Each door's line says "public from Oct 3", which is true before that day and
// after it, so the words need no clock and no second deploy. Judge mode's two doors speak the
// same way: judge mode is shut while the second wave of the study runs and open from the second
// lock, 2026-10-03T04:00:00Z (apps/web/lib/lock.ts, JUDGE_MODE_OPENS_UTC), and each door says
// "shut while the second wave of the study runs" and "open from Oct 3 at 04:00 UTC".
// apps/web/tests/judges.spec.ts holds those words to the instant in lock.ts.
const REPO = "https://github.com/alejandro-publius/second-look";

// No stored record answers to a sample id on the live site, so the sample record is the one a
// video walk makes on the phone, with View as FHIR at its end. The same walk's end has the city
// view of the creek it fed, which is the full city page; the live creek's own page stays empty
// until a real check arrives, and the city door's line says so (CRITIC_02 D05).
const walk = content.walks[0];
const walkHref = `/walk/${walk?.id ?? ""}`;
const clip = { seconds: walk?.clip.seconds ?? "" };

// A stamp shows each line of the audit log as it was on the day of the stamp, not the day it was
// written, so the door says no line has changed since that day, read from the committed log and
// results/ots.json when the page is built (CRITIC_09 Q03). With no stamp over the whole log it
// claims none.
const stampDay = logStampDay(auditEntries(), otsStatus().proofs);

// The judges' front door. The participant's front door, /, carries the wordmark and About and
// nothing else, so a person taking the test is never one tap from the answer key or the code.
// Judge mode leads because it stores nothing. The door to the AI's one question comes second: it
// is the one place on the site where a judge meets the checker's question, it stores nothing
// either, and it stood last of eighteen doors, five screens down (audit finding
// first-two-minutes-1). The real test is the study, so it comes after both and says so, and a
// judge's first taps never add a session to the data. Every door has one line under
// it: what it shows and about how long it takes (CRITIC_02 D03 and D11). The clip's length is on
// one door only, and the door to the city view says it is the end of a walk (CRITIC_09 Q04).
// The clips show natural creeks, so an honest walk finds little for a city to do. The city door
// says how to see a measure, in the same words the walk itself shows (CRITIC_09 Q01).
const DOORS: { href: string; label: string; note: string; params?: Record<string, string | number> }[] = [
  { href: "/demo", label: "judges.demo", note: "judges.demo_note" },
  { href: "/t?src=other", label: "judges.take_test", note: "judges.take_test_note" },
  { href: "/check", label: "judges.check", note: "judges.check_note" },
  { href: "/walk", label: "judges.walks", note: "judges.walks_note" },
  { href: walkHref, label: "judges.record", note: "judges.record_note", params: clip },
  { href: walkHref, label: "judges.city", note: "judges.city_note", params: { button: t("walk.city_link"), honest: t("walk.honest_note") } },
  { href: "/two", label: "judges.two", note: "judges.two_note" },
  { href: "/how-we-know", label: "judges.how", note: "judges.how_note" },
  { href: `${REPO}#for-judges`, label: "judges.readme", note: "judges.readme_note" },
  // The two docs the README's For judges table leads with, one tap from here (critic round 14 R12).
  { href: `${REPO}/blob/main/docs/JUDGE_DAY.md`, label: "judges.day", note: "judges.day_note" },
  { href: `${REPO}/blob/main/docs/submission/JUDGE_QA.md`, label: "judges.qa", note: "judges.qa_note" },
  { href: `${REPO}/blob/main/docs/REPORT.pdf`, label: "judges.report", note: "judges.report_note" },
  { href: `${REPO}/blob/main/docs/MODEL_CARD.md`, label: "judges.model_card", note: "judges.model_card_note" },
  { href: `${REPO}/blob/main/examples/footage-flag/README.md`, label: "judges.ai_example", note: "judges.ai_example_note" },
  { href: REPO, label: "judges.repo", note: "judges.repo_note" },
  { href: "/verify", label: "judges.verify", note: stampDay ? "judges.verify_note" : "judges.verify_note_unstamped", params: { date: stampDay ?? "" } },
  { href: "/credits", label: "nav.credits", note: "judges.credits_note" },
];

type Door = (typeof DOORS)[number];

function door(d: Door) {
  return (
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
  );
}

export default function JudgesPage() {
  return (
    <div className="stack">
      <FocusHeading>{t("judges.title")}</FocusHeading>
      {/* The first paragraph gives no duration. The landing page's line, frozen with the test flow,
          says two minutes, while the doors below say about four for the test with its lesson, so
          this page opens with its own line instead (CRITIC_04 F04). */}
      <p>{t("judges.intro")}</p>
      <nav className="card" aria-label={t("judges.title")}>
        {DOORS.slice(0, 1).map(door)}
        {/* Part 2's judge mode (UPDATE_31 section 2 item 9): feel the checker's question. */}
        <JudgesAssistDoor />
        {DOORS.slice(1).map(door)}
      </nav>
    </div>
  );
}
