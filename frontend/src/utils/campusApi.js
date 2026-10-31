/** CampusFlow Phase 9.9.3.2 — cancellable API requests. */
export class CampusApiError extends Error {
  constructor(message, status = null, code = "API_ERROR") {
    super(message);
    this.name = "CampusApiError";
    this.status = status;
    this.code = code;
  }
}

function wait(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(new CampusApiError("Request cancelled.", null, "CANCELLED"));
    const timer = setTimeout(() => { cleanup(); resolve(); }, ms);
    const onAbort = () => { clearTimeout(timer); cleanup(); reject(new CampusApiError("Request cancelled.", null, "CANCELLED")); };
    function cleanup() { signal?.removeEventListener("abort", onAbort); }
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

export async function campusApiRequest(url, { method = "GET", body, headers = {}, signal, timeout = 12000, retries = 0 } = {}) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    if (signal?.aborted) throw new CampusApiError("Request cancelled.", null, "CANCELLED");
    const controller = new AbortController();
    let timedOut = false;
    const onAbort = () => controller.abort();
    signal?.addEventListener("abort", onAbort, { once: true });
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeout);
    try {
      const response = await fetch(url, {
        method,
        headers: { ...(body !== undefined ? { "Content-Type": "application/json" } : {}), ...headers },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
      });
      let data;
      try { data = await response.json(); }
      catch { throw new CampusApiError("The server returned an invalid response.", response.status, "INVALID_RESPONSE"); }
      if (!response.ok) {
        throw new CampusApiError(typeof data.detail === "string" ? data.detail : "The request could not be completed.", response.status, "HTTP_ERROR");
      }
      return data;
    } catch (error) {
      const normalized = signal?.aborted
        ? new CampusApiError("Request cancelled.", null, "CANCELLED")
        : timedOut
          ? new CampusApiError("The server took too long to respond.", null, "TIMEOUT")
          : error instanceof CampusApiError
            ? error
            : new CampusApiError("Unable to connect to CampusFlow.", null, "NETWORK_ERROR");
      const retryable = ["TIMEOUT", "NETWORK_ERROR"].includes(normalized.code) || [502, 503, 504].includes(normalized.status);
      if (!retryable || attempt === retries || signal?.aborted) throw normalized;
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
    }
    await wait(400 * (attempt + 1), signal);
  }
}
