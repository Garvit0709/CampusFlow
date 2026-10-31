
import { useEffect, useState } from "react";

/**
 * Tracks the browser's reported network state.
 *
 * navigator.onLine is only a connectivity hint.
 * It does not guarantee the FastAPI server is reachable.
 */

export default function useNetworkStatus() {
  const [online, setOnline] = useState(
    () => typeof navigator === "undefined"
      ? true
      : navigator.onLine
  );

  const [restored, setRestored] = useState(false);

  useEffect(() => {
    function handleOnline() {
      setOnline(true);
      setRestored(true);
    }

    function handleOffline() {
      setOnline(false);
      setRestored(false);
    }

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  function dismissRestored() {
    setRestored(false);
  }

  return {
    online,
    restored,
    dismissRestored,
  };
}
