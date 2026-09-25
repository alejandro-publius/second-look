import Link from "next/link";
import { Row } from "./ui/Row";
import { t } from "@/lib/t";

/**
 * The judges' door to part 2's judge mode (UPDATE_31 section 2 item 9): the eight photos as the
 * assisted arm meets them, with feedback and nothing stored, so a judge feels the question.
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
