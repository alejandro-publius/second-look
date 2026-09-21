import type { TestAnswer } from "@/lib/api";
import { t } from "@/lib/t";

export function AnswerButtons({ onAnswer, disabled = false }: { onAnswer: (a: TestAnswer) => void; disabled?: boolean }) {
  return (
    <div className="answer-row" role="group" aria-label={t("test.answer_group")}>
      <button type="button" className="btn" disabled={disabled} onClick={() => onAnswer("yes")}>
        {t("test.yes")}
      </button>
      <button type="button" className="btn" disabled={disabled} onClick={() => onAnswer("no")}>
        {t("test.no")}
      </button>
      <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => onAnswer("cant_tell")}>
        {t("test.cant_tell")}
      </button>
    </div>
  );
}
