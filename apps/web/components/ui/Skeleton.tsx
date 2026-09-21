/**
 * A loading state in the shape of what is coming, never a spinner. The words are announced; the
 * blocks are decoration for the eye only.
 */
export function Skeleton({ label, lines = 2, photo = true }: { label: string; lines?: number; photo?: boolean }) {
  return (
    <div className="stack">
      <p role="status" className="muted">
        {label}
      </p>
      <div aria-hidden="true" className="stack">
        {photo ? <div className="skeleton skeleton-photo" /> : null}
        {Array.from({ length: lines }, (_, i) => (
          <div key={i} className="skeleton skeleton-line" />
        ))}
      </div>
    </div>
  );
}
