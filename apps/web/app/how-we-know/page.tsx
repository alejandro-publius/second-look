import type { Metadata } from "next";
import { Row } from "@/components/ui/Row";
import { content, featureById, licenseUrl } from "@/lib/content";
import { GATE_FILES, PASS_FILE, footageExample, howWeKnowNumbers } from "@/lib/how-data";
import { t } from "@/lib/t";

type Case = {
  frame: string;
  model: string;
  feature: string;
  credit: { author: string; license: string; source_url: string };
};

// The rows both cases open with, and the frame's credit they close with: the author, the licence
// and the video it was taken from, as /credits and the walk credit a clip (CRITIC_03 D04).
function CaseRows({ c }: { c: Case }) {
  return (
    <>
      <Row label={t("how.example_frame")} value={<span className="hash">{c.frame}</span>} />
      <Row label={t("how.example_model")} value={<span className="hash">{c.model}</span>} />
      <Row label={t("how.example_feature")} value={featureById(c.feature)?.name ?? c.feature} />
    </>
  );
}

function FrameCredit({ c }: { c: Case }) {
  const url = licenseUrl(c.credit.license);
  return (
    <p className="small muted" data-testid="frame-credit">
      {t("how.example_credit", { author: c.credit.author })}{" "}
      {url ? (
        <a href={url} rel="license noreferrer">
          {c.credit.license}
        </a>
      ) : (
        c.credit.license
      )}
      {". "}
      <a href={c.credit.source_url} rel="noreferrer nofollow">
        {t("credits.source")}
      </a>
    </p>
  );
}

export const metadata: Metadata = { title: `${t("how.title")}: ${t("app.name")}` };

// The plan was tagged prereg-v1 on 2026-09-21, before any participant, and a tag is never moved
// (hard rules 13 and 15), so the page names it as made (REVIEW_03 R30).
const PLAN_TAG = process.env.NEXT_PUBLIC_PLAN_TAG || "prereg-v1";

const featureNames = (ids: string[]) =>
  ids.length ? ids.map((id) => featureById(id)?.name ?? id).join(", ") : t("how.none");

// "Sep 24, 2026", as /credits writes a date, so it never breaks at a hyphen on a phone.
function runDay(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-US", { dateStyle: "medium", timeZone: "UTC" });
}

// Static. The pass table and the gate's footage run are read from results/ when the page is built
// (lib/how-data.ts), the way /verify reads the audit log, so the numbers here are the committed
// ones (CRITIC_02 D03). A part whose file is missing or not real is left out.
export default function HowWeKnowPage() {
  const { pass, gate } = howWeKnowNumbers(content.features.map((f) => f.id));
  const example = footageExample();
  return (
    <article className="stack">
      <h1>{t("how.title")}</h1>
      <p>{t("how.intro")}</p>
      <h2>{t("how.plan_title")}</h2>
      <p>{t("how.plan", { tag: PLAN_TAG })}</p>
      <h2>{t("how.flow_title")}</h2>
      <ol>
        <li>{t("how.flow_1")}</li>
        <li>{t("how.flow_2")}</li>
        <li>{t("how.flow_3")}</li>
        <li>{t("how.flow_4")}</li>
        <li>{t("how.flow_5")}</li>
      </ol>
      <h2>{t("how.numbers_title")}</h2>
      <p>{t("how.numbers")}</p>
      <h2>{t("how.ai_title")}</h2>
      <p>{t("how.ai")}</p>
      {pass ? (
        <section className="stack" aria-labelledby="how-pass">
          <h3 id="how-pass">{t("how.pass_title")}</h3>
          <p>{t("how.pass_intro", { models: pass.models.length })}</p>
          <div className="card" data-testid="pass-table">
            {pass.models.map((m) => (
              <Row
                key={m.model}
                label={<span className="hash">{m.model}</span>}
                value={
                  <>
                    {t("how.passed", { list: featureNames(m.passed) })}
                    <br />
                    {t("how.not_passed", { list: featureNames(m.failed) })}
                  </>
                }
              />
            ))}
          </div>
          <p className="small muted">{t("how.from", { files: PASS_FILE, date: runDay(pass.date) })}</p>
        </section>
      ) : null}
      {gate ? (
        <section className="stack" aria-labelledby="how-gate">
          <h3 id="how-gate">{t("how.gate_title")}</h3>
          <p className="tabular" data-testid="gate-numbers">
            {t("how.gate", {
              frames: gate.frames,
              videos: gate.videos,
              candidates: gate.candidates,
              dropped: gate.dropped,
              kept: gate.kept,
            })}
          </p>
          <p>{t("how.gate_rule")}</p>
          <p className="small muted">{t("how.from", { files: GATE_FILES.join(", "), date: runDay(gate.date) })}</p>
        </section>
      ) : null}
      {/* The footage example, read from examples/footage-flag/example.json when the page is built
          (CRITIC_03 D04). The model's words reach the page in one place only: the kept flag's
          note, after "the checker noticed" (hard rule 5). The dropped flag's note is never shown. */}
      {example ? (
        <section className="stack" aria-labelledby="how-example">
          <h3 id="how-example">{t("how.example_title")}</h3>
          <p>{t("how.example_intro")}</p>
          {example.kept ? (
            <div className="card stack" data-testid="example-kept">
              <h4>{t("how.example_kept_title")}</h4>
              <CaseRows c={example.kept} />
              <p>{t("how.example_kept", { photos: example.kept.photos, right: example.kept.right, runs: example.kept.runs })}</p>
              <p>{t("how.example_question")}</p>
              {/* The same words and the same shape as the walk's checker question (WalkFlow.tsx). */}
              <div className="card stack" data-testid="example-question">
                <p>
                  <strong>{example.kept.question}</strong>
                </p>
                <p className="small muted" data-testid="example-note">
                  {t("label.checker_noticed")}: {example.kept.note}
                </p>
              </div>
              <FrameCredit c={example.kept} />
            </div>
          ) : null}
          {example.dropped ? (
            <div className="card stack" data-testid="example-dropped">
              <h4>{t("how.example_dropped_title")}</h4>
              <CaseRows c={example.dropped} />
              <p>
                {example.dropped.not_passed
                  ? t("how.example_dropped", { photos: example.dropped.photos, right: example.dropped.right, runs: example.dropped.runs })
                  : t("how.example_dropped_other")}
              </p>
              <p className="small muted">
                {t("how.example_gate_words")}{" "}
                <span className="hash" data-testid="example-reason">
                  {example.dropped.reasons.join("; ")}
                </span>
              </p>
              <FrameCredit c={example.dropped} />
            </div>
          ) : null}
          <p className="small muted">{t("how.from", { files: example.files.join(", "), date: runDay(example.date) })}</p>
        </section>
      ) : null}
    </article>
  );
}
