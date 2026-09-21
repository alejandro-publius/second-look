"use client";

import { ChoiceList } from "./ui/ChoiceList";
import type { TestAnswer } from "@/lib/api";
import { t } from "@/lib/t";

/**
 * Yes, No, Can't tell: three buttons of equal weight, stacked, in a fixed order. They are never
 * coloured green and red, because colour would tell the person which answer is the safe one and
 * that would bend the study.
 */
export function AnswerButtons({ onAnswer, disabled = false }: { onAnswer: (a: TestAnswer) => void; disabled?: boolean }) {
  return (
    <div className="actions">
      <ChoiceList<TestAnswer>
        groupLabel={t("test.answer_group")}
        disabled={disabled}
        onChoose={onAnswer}
        choices={[
          { value: "yes", label: t("test.yes") },
          { value: "no", label: t("test.no") },
          { value: "cant_tell", label: t("test.cant_tell") },
        ]}
      />
    </div>
  );
}
