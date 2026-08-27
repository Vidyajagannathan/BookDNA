export function Brand({ small = false }: { small?: boolean }) {
  return (
    <span className={`brand-lockup${small ? " small" : ""}`}>
      <span className="brand-marks" aria-hidden="true">
        <img className="brand-mark brand-mark-light" src="/brand/bookdna-mark-light.svg" alt="" />
        <img className="brand-mark brand-mark-dark" src="/brand/bookdna-mark-dark.svg" alt="" />
      </span>
      <span className="brand-wordmark"><span>BOOK</span><i>DNA</i></span>
    </span>
  );
}
