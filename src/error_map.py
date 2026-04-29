from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ErrorInfo:
    code: str
    category: str
    message: str
    status: int


ERROR_MAP: dict[str, ErrorInfo] = {
    "timeout": ErrorInfo("timeout", "timeout", "Request timed out", 504),
    "network": ErrorInfo("network", "network", "Network failure", 502),
    "quota": ErrorInfo("quota", "quota", "Upstream quota exceeded", 429),
    "upstream_4xx": ErrorInfo("upstream_4xx", "upstream_4xx", "Upstream client error", 502),
    "upstream_5xx": ErrorInfo("upstream_5xx", "upstream_5xx", "Upstream server error", 502),
    "malformed_response": ErrorInfo("malformed_response", "malformed_response", "Malformed upstream response", 502),
    "policy_rejected": ErrorInfo("policy_rejected", "policy_rejected", "Request rejected by retry policy", 400),
    "unknown": ErrorInfo("unknown", "network", "Relay failure", 502),
}


def to_client_error(reason: str | None) -> dict:
    info = ERROR_MAP.get(reason or "", ERROR_MAP["unknown"])
    return {
        "error": {
            "code": info.code,
            "category": info.category,
            "message": info.message,
            "status": info.status,
        }
    }
