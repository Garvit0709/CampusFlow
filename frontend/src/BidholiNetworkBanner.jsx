
import "./BidholiRouteFeedback.css";

export default function BidholiNetworkBanner({
  online,
  restored,
  onDismiss,
  onRetry,
}) {
  if (!online) {
    return (
      <div
        className="cf-network-banner cf-network-offline"
        role="status"
        aria-live="polite"
      >
        <span aria-hidden="true">⚠</span>

        <div>
          <strong>You're offline</strong>
          <p>
            New routes may be unavailable.
            Previously displayed directions remain
            visible while this page stays open.
          </p>
        </div>
      </div>
    );
  }

  if (restored) {
    return (
      <div
        className="cf-network-banner cf-network-restored"
        role="status"
        aria-live="polite"
      >
        <span aria-hidden="true">✓</span>

        <div>
          <strong>Connection restored</strong>
          <p>
            You can calculate walking routes again.
          </p>

          <div className="cf-network-actions">
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
              >
                Retry Route
              </button>
            )}

            <button
              type="button"
              onClick={onDismiss}
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
