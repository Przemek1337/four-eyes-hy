import { useLive } from "../live";

/** Shown when every recent poll failed after data had loaded. The panels keep their last data; this says why they stopped
 * moving. Before anything has loaded, the full-page GatewayScreen takes over instead. */
export function ConnectionBanner() {
  const { offline, loadedOnce, refreshNow } = useLive();
  if (!offline || !loadedOnce) return null;
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
