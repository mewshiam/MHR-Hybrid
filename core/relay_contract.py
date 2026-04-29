"""Shared relay contract for worker/apps-script backends."""

from __future__ import annotations

import base64
from dataclasses import dataclass


@dataclass(slots=True)
class RelayRequest:
    m: str
    u: str
    h: dict
    b: bytes = b""
    ct: str | None = None
    r: bool = True

    def to_payload(self) -> dict:
        payload = {"m": self.m.upper(), "u": self.u, "r": bool(self.r)}
        headers = {str(k): str(v) for k, v in (self.h or {}).items()}
        if headers:
            payload["h"] = headers
        if self.b:
            payload["b"] = base64.b64encode(self.b).decode()
            if self.ct:
                payload["ct"] = self.ct
        return payload

    @classmethod
    def from_inputs(cls, method: str, url: str, headers: dict | None, body: bytes | None):
        hdrs = dict(headers or {})
        filt = {k: v for k, v in hdrs.items() if k.lower() != "accept-encoding"}
        ct = hdrs.get("Content-Type") or hdrs.get("content-type")
        return cls(m=method.upper(), u=str(url), h=filt if filt else hdrs, b=body or b"", ct=ct)


@dataclass(slots=True)
class RelayResponse:
    s: int
    h: dict
    b: bytes
    e: str | None = None

    def to_output(self) -> dict:
        out = {"s": int(self.s), "h": self.h or {}, "b": base64.b64encode(self.b).decode(), "e": self.e}
        return out


def parse_response_json(data: dict) -> RelayResponse:
    if not isinstance(data, dict):
        raise ValueError("relay response must be object")
    status = int(data.get("s", 200))
    headers = data.get("h", {})
    if not isinstance(headers, dict):
        headers = {}
    raw_b = data.get("b", "")
    if isinstance(raw_b, bytes):
        body = raw_b
    elif isinstance(raw_b, str):
        try:
            body = base64.b64decode(raw_b)
        except Exception as exc:
            raise ValueError("relay response body is not valid base64") from exc
    else:
        body = b""
    err = data.get("e")
    return RelayResponse(s=status, h=headers, b=body, e=str(err) if err is not None else None)
