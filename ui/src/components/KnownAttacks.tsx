import type { SignaturesT } from "../api/types";

/** Historical attacks the signature feed recognises, and how many it stopped. The feed comes from outside the gateway. */
export function KnownAttacks({ signatures }: { signatures: SignaturesT }) {
  return (
    <section className="subsec" aria-label="Known attacks blocked">
      <h3>Known attacks blocked</h3>
      <p className="sub">From the signature feed, which an outside system can update.</p>
      {signatures.hits.length === 0 ? (
        <p className="state">No known attack has been seen yet.</p>
      ) : (
        <div className="table-scroll">
          <table className="ctab">
            <thead><tr><th>Type</th><th>Matches</th><th>Reference</th><th>Blocked</th></tr></thead>
            <tbody>
              {signatures.hits.map((h) => (
                <tr key={`${h.type}-${h.signature_id ?? h.reference}`}>
                  <td><code>{h.type}</code></td>
                  <td className="muted">{h.matches}</td>
                  <td className="muted">{h.signature_id ? `${h.signature_id} · ` : ""}{h.reference}</td>
                  <td className="num">{h.blocked}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
