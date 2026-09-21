/** A label, a value, and an optional gauge at the right. One row shape for the whole product. */
export function Row({ label, value, end }: { label: React.ReactNode; value?: React.ReactNode; end?: React.ReactNode }) {
  return (
    <div className="row">
      <span className="row-label">
        {label}
        {value ? (
          <>
            <br />
            <span className="row-value">{value}</span>
          </>
        ) : null}
      </span>
      {end ? <span className="row-end">{end}</span> : null}
    </div>
  );
}
