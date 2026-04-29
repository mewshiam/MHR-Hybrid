from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass

from core.relay_contract import RelayRequest

log = logging.getLogger("Fronter")


@dataclass(slots=True)
class RelayAttempt:
    backend: str
    reason: str


class RelayAdapterBase:
    backend = "unknown"

    async def send(self, request: RelayRequest) -> dict:
        raise NotImplementedError


class AppsScriptAdapter(RelayAdapterBase):
    backend = "apps_script"

    def __init__(self, fronter):
        self.fronter = fronter

    async def send(self, request: RelayRequest) -> dict:
        return await self.fronter._relay_apps_script_payload(request.to_payload())


class WorkerAdapter(RelayAdapterBase):
    backend = "worker"

    def __init__(self, fronter):
        self.fronter = fronter

    async def send(self, request: RelayRequest) -> dict:
        from urllib.parse import urlparse
        parsed = urlparse(request.u)
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"
        host = parsed.netloc
        lines = [f"{request.m} {path} HTTP/1.1", f"Host: {host}"]
        for k, v in request.h.items():
            if k.lower() == "host":
                continue
            lines.append(f"{k}: {v}")
        lines.append(f"Content-Length: {len(request.b)}")
        raw_req = ("\r\n".join(lines) + "\r\n\r\n").encode() + request.b
        raw = await self.fronter.forward(raw_req)
        return self.fronter._http_bytes_to_contract(raw)


def should_fallback(exc: Exception | None = None, response: dict | None = None) -> str | None:
    if exc is not None:
        if isinstance(exc, asyncio.TimeoutError):
            return "timeout"
        txt = str(exc).lower()
        if "json" in txt or "malformed" in txt or "decode" in txt:
            return "malformed_json"
        return "error"

    if response is None:
        return "empty"

    if response.get("e"):
        return "backend_error"

    status = int(response.get("s", 0) or 0)
    if status == 429 or status >= 500:
        return f"status_{status}"
    return None
