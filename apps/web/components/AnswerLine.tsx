/**
 * One answer in a record: the question, the answer, and beside them what the observer's score says
 * about it. /spot lists a stored visit's answers with it, and the walk's record screen lists the
 * answers a walk made on the phone the same way (CRITIC_04 F01).
 */
export function AnswerLine({ text, value, score }: { text: string; value: string; score: string }) {
  return (
    <div className="answer-line">
      <span>
        <span className="small muted">{text}</span>
        <br />
        <strong>{value}</strong>
      </span>
      <span className="observer">{score}</span>
    </div>
  );
}
