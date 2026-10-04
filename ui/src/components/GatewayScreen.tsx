import { useLive } from "../live";

/** The four eyes, large, opening and closing in turn clockwise. Decoration only: the text carries the meaning. */
function WatchingEyes() {
  return (
    <span className="gw-eyes" aria-hidden="true"><i /><i /><i /><i /></span>
  );
}

/**
 * Full-page screen while nothing has loaded yet: connecting at first, then "not responding" when the gateway stays
 * silent. The page behind it keeps polling, so the screen leaves by itself on the first answer.
 */
export function GatewayScreen() {
  const { offline, loadedOnce, refreshNow } = useLive();
  if (loadedOnce) return null;
  return (
    <div className="gw-screen" role={offline ? "alert" : undefined} aria-live="polite" aria-busy={!offline}>
      <WatchingEyes />
      <span className="gw-name" aria-hidden="true">FourEyes</span>
      {offline ? (
        <div className="gw-text">
          <b>The gateway is not responding.</b>
          <span>Trying again every 5 seconds.</span>
          <button className="btn-sm" onClick={refreshNow}>Retry now</button>
        </div>
      ) : (
        <div className="gw-text">
          <b>Connecting to the gateway…</b>
          <span>Checking every 5 seconds.</span>
        </div>
      )}
    </div>
  );
}
