"use client";

/**
 * One thing per page: large stacked choices of equal weight in a fixed order, each one hit target
 * with no dead zone. Used for Yes, No, Can't tell and for radio choices. The order never changes
 * and no choice is coloured, because colouring one would tell the person what to answer.
 */
export interface Choice<T extends string> {
  value: T;
  label: string;
  hint?: string;
}

export function ChoiceList<T extends string>({
  choices,
  onChoose,
  selected,
  disabled = false,
  groupLabel,
}: {
  choices: Choice<T>[];
  onChoose: (value: T) => void;
  selected?: T | null;
  disabled?: boolean;
  groupLabel: string;
}) {
  return (
    <div className="choice-list" role="group" aria-label={groupLabel}>
      {choices.map((c) => (
        <button
          key={c.value}
          type="button"
          className="choice"
          data-answer={c.value}
          disabled={disabled}
          aria-pressed={selected === undefined ? undefined : selected === c.value}
          onClick={() => onChoose(c.value)}
        >
          <span>
            {c.label}
            {c.hint ? <span className="small muted"> {c.hint}</span> : null}
          </span>
        </button>
      ))}
    </div>
  );
}
