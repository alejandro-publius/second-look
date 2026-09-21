"use client";

import { Button } from "./ui/Button";
import { ChoiceList } from "./ui/ChoiceList";
import type { TestAnswer } from "@/lib/api";
import { t } from "@/lib/t";

/**
 * Yes, No, Can't tell: three buttons of equal weight, stacked, in a fixed order. They are never
 * coloured green and red, because colour would tell the person which answer is the safe one and
 * that would bend the study. A tap selects; Next confirms. Nothing is on a clock, so a mis-tap
 * can be changed until Next, which is the accessible pattern and needs no undo timer.
 */
export function AnswerButtons({
  onAnswer,
  selected,
  onConfirm,
  disabled = false,
}: {
  onAnswer: (a: TestAnswer) => void;
  selected: TestAnswer | null;
  onConfirm: () => void;
  disabled?: boolean;
}) {
  return (
    <div className="actions">
      <ChoiceList<TestAnswer>
        groupLabel={t("test.answer_group")}
        disabled={disabled}
        selected={selected}
        onChoose={onAnswer}
        choices={[
          { value: "yes", label: t("test.yes") },
          { value: "no", label: t("test.no") },
          { value: "cant_tell", label: t("test.cant_tell") },
        ]}
      />
      <Button block disabled={disabled || selected === null} data-confirm="" onClick={onConfirm}>
        {t("test.confirm")}
      </Button>
    </div>
  );
}
