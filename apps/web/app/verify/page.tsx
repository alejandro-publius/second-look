import type { Metadata } from "next";
import { VerifyLog } from "@/components/VerifyLog";
import { headsAgainstLog, verifyChain } from "@/lib/chain";
import { t } from "@/lib/t";
import { auditEntries, otsStatus } from "@/lib/verify-data";
import { proofName, proofStatus } from "@/lib/verify-text";

export const metadata: Metadata = {
  title: `${t("verify.title")}: ${t("app.name")}`,
  description: t("verify.meta"),
};

// Static. The audit log and results/ots.json are read when the page is built, and the chain is
// checked then with the rule in lib/chain.ts; the browser runs the same check again on load.
// OpenTimestamps is a public timestamp service, not ours: the page says so before it shows a proof.
export default async function VerifyPage() {
  const entries = auditEntries();
  const ots = otsStatus();
  const built = await verifyChain(entries);
  const heads = headsAgainstLog(ots.proofs, entries);
  const plan = ots.proofs.filter((p) => p.what !== "audit_head");

  return (
    <article className="stack">
      <h1>{t("verify.title")}</h1>
      <p>{t("verify.intro")}</p>

      <h2>{t("verify.log_title")}</h2>
      <p>{t("verify.log_body")}</p>
      <VerifyLog entries={entries} proofs={heads} built={built} />

      <h2>{t("verify.ots_title")}</h2>
      <p>{t("verify.ots_what")}</p>
      <p>{t("verify.ots_why")}</p>
      <ul className="stack verify-proofs" aria-label={t("verify.ots_title")}>
        {[...plan, ...heads].map((p) => (
          <li key={p.proof} className="card" data-testid={`proof-${p.what}`}>
            <h3>{proofName(p)}</h3>
            <p>{proofStatus(p)}</p>
            <p className="small muted hash">{p.proof}</p>
          </li>
        ))}
      </ul>
      {ots.checked_utc ? <p className="small muted">{t("verify.ots_checked", { time: ots.checked_utc })}</p> : null}

      <h2>{t("verify.check_title")}</h2>
      <p>{t("verify.check_body")}</p>
      <pre className="code">{[t("verify.cmd_audit"), t("verify.cmd_tag"), t("verify.cmd_plan"), t("verify.cmd_head")].join("\n")}</pre>
      <p className="small muted">{t("verify.cmd_note")}</p>
    </article>
  );
}
