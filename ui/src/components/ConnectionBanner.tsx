import { useLive } from "../live";

/** Shown when every recent poll failed. The panels keep their last data; this says why they stopped moving. */
export function ConnectionBanner() {
  const { offline, refreshNow } = useLive();
  if (!offline) return null;
  return (
    <div className="alertbar offline" role="alert">
      <span className="badge badge-red">Offline</span>
      <div>
        <b>The gateway is not responding.</b>
        <span>Panels show the last data they loaded. Trying again every 5 seconds.</span>
      </div>
      <button className="btn-sm" onClick={refreshNow}>Retry now</button>
    </div>
  );
}
