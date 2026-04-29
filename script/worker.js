const WORKER_URL = "myworker.workers.dev";

const ALLOWED_METHODS = new Set(["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]);
const HOP_HEADER = "x-relay-hop";
const ORIGIN_MARKER = "x-relay-origin";
const ORIGIN_VALUE = "cfw";
const MAX_JSON_BYTES = 256 * 1024;
const MAX_BODY_BASE64_BYTES = 10 * 1024 * 1024;
const MAX_HEADER_NAME_BYTES = 128;
const MAX_HEADER_VALUE_BYTES = 8192;
const MAX_HEADERS = 128;
const BUDGET_MS = 50_000;
const SAFETY_BUFFER_MS = 1_500;

export default {
  async fetch(request, env, ctx) {
    const startedAt = Date.now();

    try {
      if (request.method !== "POST") {
        return err(405, "METHOD_NOT_ALLOWED", "only POST is accepted", startedAt);
      }

      if (request.headers.get(HOP_HEADER) === "1" || request.headers.get(ORIGIN_MARKER) === ORIGIN_VALUE) {
        return err(508, "LOOP_DETECTED", "loop detected", startedAt);
      }

      const contentLen = Number(request.headers.get("content-length") || 0);
      if (contentLen > MAX_JSON_BYTES) {
        return err(413, "REQUEST_TOO_LARGE", "payload too large", startedAt);
      }

      const req = await request.json();
      if (!req || typeof req !== "object") {
        return err(400, "BAD_REQUEST", "invalid json payload", startedAt);
      }

      if (!req.u || typeof req.u !== "string") {
        return err(400, "MISSING_URL", "missing url", startedAt);
      }

      const targetUrl = parseUrl(req.u);
      if (targetUrl.error) return err(400, targetUrl.error.code, targetUrl.error.message, startedAt);

      if (remainingMs(startedAt) <= SAFETY_BUFFER_MS) {
        return err(503, "BUDGET_LOW", "processing budget too low", startedAt);
      }

      const method = String(req.m || "GET").toUpperCase();
      if (!ALLOWED_METHODS.has(method)) {
        return err(400, "METHOD_BLOCKED", "method not allowed", startedAt);
      }

      const headersResult = sanitizeHeaders(req.h);
      if (headersResult.error) {
        return err(400, headersResult.error.code, headersResult.error.message, startedAt);
      }

      const headers = headersResult.headers;
      headers.set(HOP_HEADER, "1");
      headers.set(ORIGIN_MARKER, ORIGIN_VALUE);

      const fetchOptions = {
        method,
        headers,
        redirect: req.r === false ? "manual" : "follow"
      };

      if (req.b) {
        if (typeof req.b !== "string" || req.b.length > MAX_BODY_BASE64_BYTES) {
          return err(413, "BODY_TOO_LARGE", "request body exceeds limit", startedAt);
        }
        const binary = Uint8Array.from(atob(req.b), c => c.charCodeAt(0));
        fetchOptions.body = binary;
      }

      const timeoutMs = Math.max(1000, remainingMs(startedAt) - SAFETY_BUFFER_MS);
      if (timeoutMs <= 1000) {
        return err(503, "BUDGET_LOW", "insufficient budget for subrequest", startedAt);
      }

      const aborter = new AbortController();
      const timer = setTimeout(() => aborter.abort("SUBREQUEST_TIMEOUT"), timeoutMs);
      fetchOptions.signal = aborter.signal;

      let resp;
      try {
        resp = await fetch(targetUrl.href, fetchOptions);
      } catch (fetchErr) {
        const classified = classifyFailure(fetchErr);
        return err(classified.status, classified.code, classified.message, startedAt);
      } finally {
        clearTimeout(timer);
      }

      const buffer = await resp.arrayBuffer();
      const uint8 = new Uint8Array(buffer);

      let binary = "";
      const chunkSize = 0x8000;
      for (let i = 0; i < uint8.length; i += chunkSize) {
        binary += String.fromCharCode.apply(null, uint8.subarray(i, i + chunkSize));
      }

      const base64 = btoa(binary);
      const responseHeaders = {};
      resp.headers.forEach((v, k) => {
        responseHeaders[k] = v;
      });

      return json({
        ok: true,
        s: resp.status,
        h: responseHeaders,
        b: base64,
        code: "OK",
        elapsedMs: Date.now() - startedAt,
        budgetRemainingMs: remainingMs(startedAt)
      });

    } catch (err) {
      const classified = classifyFailure(err);
      return errResponse(classified.status, classified.code, classified.message, startedAt);
    }
  }
};

function parseUrl(value) {
  try {
    const url = new URL(value);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return { error: { code: "URL_SCHEME_BLOCKED", message: "only http/https are allowed" } };
    }
    if (url.username || url.password) {
      return { error: { code: "URL_CREDENTIALS_BLOCKED", message: "credentials in url are not allowed" } };
    }
    if ([WORKER_URL].some(h => url.hostname.endsWith(h))) {
      return { error: { code: "SELF_FETCH_BLOCKED", message: "self-fetch blocked" } };
    }
    return { url };
  } catch {
    return { error: { code: "URL_INVALID", message: "invalid url" } };
  }
}

function sanitizeHeaders(input) {
  const headers = new Headers();
  if (!input || typeof input !== "object") return { headers };

  const blocked = new Set(["host", "connection", "content-length", "transfer-encoding", HOP_HEADER, ORIGIN_MARKER]);
  let count = 0;

  for (const [k, v] of Object.entries(input)) {
    const key = String(k || "").trim();
    if (!key || blocked.has(key.toLowerCase())) continue;
    if (key.length > MAX_HEADER_NAME_BYTES) {
      return { error: { code: "HEADER_NAME_TOO_LONG", message: "header name exceeds limit" } };
    }
    if (/[^\t\x20-\x7e]/.test(key)) {
      return { error: { code: "HEADER_NAME_INVALID", message: "header name contains invalid characters" } };
    }

    const value = String(v ?? "");
    if (value.length > MAX_HEADER_VALUE_BYTES) {
      return { error: { code: "HEADER_VALUE_TOO_LONG", message: "header value exceeds limit" } };
    }

    headers.set(key, value);
    count++;
    if (count > MAX_HEADERS) {
      return { error: { code: "TOO_MANY_HEADERS", message: "too many headers" } };
    }
  }

  return { headers };
}

function remainingMs(startedAt) {
  return BUDGET_MS - (Date.now() - startedAt);
}

function classifyFailure(error) {
  if (String(error).includes("SUBREQUEST_TIMEOUT") || error?.name === "AbortError") {
    return { status: 504, code: "UPSTREAM_TIMEOUT", message: "upstream request timed out" };
  }
  return { status: 502, code: "UPSTREAM_FAILURE", message: String(error?.message || error || "upstream failure") };
}

function err(status, code, message, startedAt) {
  return errResponse(status, code, message, startedAt);
}

function errResponse(status, code, message, startedAt) {
  return json({
    ok: false,
    code,
    message,
    e: message,
    elapsedMs: Date.now() - startedAt,
    budgetRemainingMs: typeof startedAt === "number" ? remainingMs(startedAt) : null
  }, status);
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {
      "content-type": "application/json"
    }
  });
}
