import { EnglishTag } from "./LanguagePicker";
import type { AnswerPiece } from "@/lib/answers";
import type { Shown } from "@/lib/lang";

/** Words in the language they are in; English inside another language carries its tag. */
function Piece({ shown }: { shown: Shown }) {
  return (
    <>
      <span lang={shown.lang}>{shown.text}</span>
      {shown.english ? (
        <>
          {" "}
          <EnglishTag />
        </>
      ) : null}
    </>
  );
}

/**
 * One answer in a record: the question, the answer, and beside them what the observer's score says
 * about it. /spot lists a stored visit's answers with it, and the walk's record screen lists the
 * answers a walk made on the phone the same way (CRITIC_04 F01).
 *
 * /spot hands over plain English words. A walk hands over each piece with its language, so an
 * answer given in Portuguese reads back in Portuguese, and English that stands in for a
 * translation says it is English.
 */
export function AnswerLine({ text, value, score }: { text: string | Shown; value: string | AnswerPiece[]; score: string }) {
  return (
    <div className="answer-line">
      <span>
        <span className="small muted">{typeof text === "string" ? text : <Piece shown={text} />}</span>
        <br />
        <strong>
          {typeof value === "string"
            ? value
            : value.map((piece, i) => (
                <span key={i}>
                  {i === 0 ? "" : (piece.join ?? ", ")}
                  <Piece shown={piece} />
                </span>
              ))}
        </strong>
      </span>
      <span className="observer">{score}</span>
    </div>
  );
}
