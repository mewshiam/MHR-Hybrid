/**
 * DomainFront Relay — Google Apps Script With Cloudflare Worker Exit
 */

const AUTH_KEY = "STRONG_SECRET_KEY";
const WORKER_URL = "https://example.workers.dev";
const HOP_HEADER = "x-relay-hop";
const ORIGIN_MARKER = "x-relay-origin";
const ORIGIN_VALUE = "gas";

const SKIP_HEADERS = {
  host: 1, connection: 1, "content-length": 1,
  "transfer-encoding": 1, "proxy-connection": 1, "proxy-authorization": 1,
};

function doPost(e) {
  try {
    var req = JSON.parse(e.postData.contents);
    if (req.k !== AUTH_KEY) return _error("UNAUTHORIZED", "unauthorized");

    if (Array.isArray(req.q)) return _doBatch(req.q);
    return _doSingle(req);

  } catch (err) {
    return _error("GAS_PARSE_ERROR", String(err));
  }
}

function _doSingle(req) {
  var validation = _validateRequest(req);
  if (validation) return validation;

  var payload = _buildWorkerPayload(req);
  var worker = _callWorker(payload);
  return _json(worker);
}

function _doBatch(items) {
  var fetchArgs = [];
  var errorMap = {};

  for (var i = 0; i < items.length; i++) {
    var item = items[i];
    var validation = _validateRequest(item);
    if (validation) {
      errorMap[i] = validation;
      continue;
    }

    var payload = _buildWorkerPayload(item);
    fetchArgs.push({
      _i: i,
      _o: {
        url: WORKER_URL,
        method: "post",
        contentType: "application/json",
        payload: JSON.stringify(payload),
        muteHttpExceptions: true,
        followRedirects: true,
        headers: _relayHeaders()
      }
    });
  }

  var responses = fetchArgs.length > 0
    ? UrlFetchApp.fetchAll(fetchArgs.map(function(x) { return x._o; }))
    : [];

  var results = [];
  var rIdx = 0;

  for (var j = 0; j < items.length; j++) {
    if (errorMap.hasOwnProperty(j)) {
      results.push(errorMap[j]);
    } else {
      var resp = responses[rIdx++];
      results.push(_normalizeWorkerResponse(resp));
    }
  }

  return _json({ q: results });
}

function _validateRequest(req) {
  if (!req || !req.u || typeof req.u !== "string") {
    return _errorObj("MISSING_URL", "missing url");
  }
  if (!req.u.match(/^https?:\/\//i)) {
    return _errorObj("URL_SCHEME_BLOCKED", "bad url");
  }
  if (req.h && typeof req.h === "object") {
    var hop = req.h[HOP_HEADER] || req.h[HOP_HEADER.toLowerCase()];
    var marker = req.h[ORIGIN_MARKER] || req.h[ORIGIN_MARKER.toLowerCase()];
    if (hop === "1" || marker === "cfw" || marker === "gas") {
      return _errorObj("LOOP_DETECTED", "loop detected");
    }
  }
  return null;
}

function _callWorker(payload) {
  var resp = UrlFetchApp.fetch(WORKER_URL, {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
    followRedirects: true,
    headers: _relayHeaders()
  });
  return _normalizeWorkerResponse(resp);
}

function _normalizeWorkerResponse(resp) {
  try {
    var parsed = JSON.parse(resp.getContentText());
    if (parsed && typeof parsed === "object") {
      if (parsed.ok === false && !parsed.code) parsed.code = "WORKER_ERROR";
      return parsed;
    }
    return _errorObj("INVALID_WORKER_RESPONSE", "invalid worker response");
  } catch (e) {
    return _errorObj("INVALID_WORKER_RESPONSE", "invalid worker response", { raw: resp.getContentText() });
  }
}

function _buildWorkerPayload(req) {
  var headers = {};

  if (req.h && typeof req.h === "object") {
    for (var k in req.h) {
      if (req.h.hasOwnProperty(k) && !SKIP_HEADERS[k.toLowerCase()] && k.toLowerCase() !== HOP_HEADER && k.toLowerCase() !== ORIGIN_MARKER) {
        headers[k] = req.h[k];
      }
    }
  }

  headers[ORIGIN_MARKER] = ORIGIN_VALUE;

  return {
    u: req.u,
    m: (req.m || "GET").toUpperCase(),
    h: headers,
    b: req.b || null,
    ct: req.ct || null,
    r: req.r !== false
  };
}

function _relayHeaders() {
  var h = {};
  h[ORIGIN_MARKER] = ORIGIN_VALUE;
  return h;
}

function doGet(e) {
  return HtmlService.createHtmlOutput("ok");
}

function _error(code, message, extra) {
  return _json(_errorObj(code, message, extra));
}

function _errorObj(code, message, extra) {
  var out = { ok: false, code: code, message: message, e: message };
  if (extra) {
    for (var k in extra) out[k] = extra[k];
  }
  return out;
}

function _json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
