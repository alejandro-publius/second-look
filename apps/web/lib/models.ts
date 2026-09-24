// A vision model's name as a person reads it, "Claude Haiku 4.5" and not its API id, the names the
// README and docs/MODEL_CARD.md use. The one mapping is in content/locales/en.json, model.<id>
// (CRITIC_04 F02). An id with no name there is shown as the id, never as a guess.
import { has, t } from "./t";

export function modelName(id: string): string {
  const key = `model.${id}`;
  return has(key) ? t(key) : id;
}
