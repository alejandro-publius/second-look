import Link from "next/link";
import { Row } from "./ui/Row";
import { t } from "@/lib/t";

/**
 * The judges' door to part 2's judge mode (UPDATE_31 section 2 item 9): the eight photos as the
 * assisted arm meets them, with feedback and nothing stored, so a judge feels the question.
 * Its line says when the question appears: only when the checker's stored answer differs from the
 * answer given, so a judge who answers every photo right is never asked (worker/src/core/assist.ts,
 * questionNeeded). apps/web/tests/part2-demo.spec.ts holds the line to results/assist_flags.json.
 */
export function JudgesAssistDoor() {
  return (
    <Row
      label={
        <Link className="row-link" href="/t2/demo">
          {t("judges.assist")}
        </Link>
      }
      value={t("judges.assist_note")}
    />
  );
}
