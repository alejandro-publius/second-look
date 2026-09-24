"use client";

import { useEffect, useState } from "react";
import { useQueryParam } from "@/components/QueryParam";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { anchorFor, verifyChain, type AuditEntry, type ChainResult, type OtsProof } from "@/lib/chain";
import { t } from "@/lib/t";
import { anchorText } from "@/lib/verify-text";

/** The chain status, a receipt look up and every line of the audit log with its receipt. */
export function VerifyLog({ entries, proofs, built }: { entries: AuditEntry[]; proofs: OtsProof[]; built: ChainResult }) {
  // null until the browser has run the check itself. The build's own result shows until then.
  const [here, setHere] = useState<ChainResult | null>(null);
  useEffect(() => {
    let live = true;
    verifyChain(entries).then((r) => live && setHere(r));
    return () => {
      live = false;
    };
  }, [entries]);

  const receipt = useQueryParam("receipt").trim().toLowerCase();
  const byHash = receipt ? entries.find((e) => e.hash === receipt) : undefined;
  const byPayload = receipt && !byHash ? entries.find((e) => e.payload_sha256 === receipt) : undefined;
  const found = byHash ?? byPayload;
  const count = entries.length;

  return (
    <>
      <ChainStatus here={here} built={built} />

      <form className="stack" action="/verify" method="get" role="search">
        <label className="field-label" htmlFor="receipt">
          {t("verify.lookup_label")}
        </label>
        <p className="small muted" id="receipt-help">
          {t("verify.lookup_help")}
        </p>
        <input key={receipt} className="text-input hash" id="receipt" name="receipt" defaultValue={receipt} autoComplete="off" spellCheck={false} aria-describedby="receipt-help" />
        <Button kind="secondary" type="submit">
          {t("verify.lookup_button")}
        </Button>
      </form>
      {receipt ? (
        <p className={`notice ${found ? "notice-ok" : "notice-warn"}`} role="status" data-testid="lookup-result">
          <Icon name={found ? "check-circle" : "warning"} />
          <span>
            {found
              ? t(byHash ? "verify.lookup_found" : "verify.lookup_found_payload", { seq: found.seq, count })
              : t("verify.lookup_none")}{" "}
            {found ? <a href={`#line-${found.seq}`}>{t("verify.lookup_go")}</a> : null}
          </span>
        </p>
      ) : null}

      <ol className="stack verify-lines" aria-label={t("verify.log_title")}>
        {entries.map((e) => {
          const anchor = anchorFor(e.seq, entries, proofs);
          return (
            <li key={e.seq} id={`line-${e.seq}`} className="card" aria-current={found?.seq === e.seq ? "true" : undefined}>
              <h3>{t("verify.entry_title", { seq: e.seq, count })}</h3>
              <p>{t(`verify.kind.${e.kind}`)}</p>
              <dl className="verify-fields">
                <dt>{t("verify.entry_when")}</dt>
                <dd className="tabular">{e.ts_utc}</dd>
                <dt>{t("verify.entry_receipt")}</dt>
                <dd className="hash" data-testid={`receipt-${e.seq}`}>
                  {e.hash}
                </dd>
                <dt>{t("verify.entry_prev")}</dt>
                <dd className={e.seq === 1 ? undefined : "hash"}>{e.seq === 1 ? t("verify.entry_first") : e.prev_hash}</dd>
                <dt>{t("verify.entry_what")}</dt>
                <dd className="hash">{e.payload_sha256}</dd>
                <dt>{t("verify.entry_anchor")}</dt>
                <dd data-testid={`anchor-${e.seq}`}>{anchorText(anchor)}</dd>
              </dl>
            </li>
          );
        })}
      </ol>
    </>
  );
}

function ChainStatus({ here, built }: { here: ChainResult | null; built: ChainResult }) {
  const result = here ?? built;
  const text = result.ok
    ? t(here ? "verify.chain_ok" : "verify.chain_ok_built", { count: result.length })
    : t(here ? "verify.chain_broken" : "verify.chain_broken_built", { line: result.line, reason: t(`verify.reason.${result.reason}`) });
  return (
    <p className={`notice ${result.ok ? "notice-ok" : "notice-bad"}`} role="status" data-testid="chain-status" data-checked={here ? "browser" : "build"}>
      <Icon name={result.ok ? "check-circle" : "warning"} />
      <span>{text}</span>
    </p>
  );
}
