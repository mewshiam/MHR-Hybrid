"""Backend routing policy for per-request relay backend selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

BackendName = Literal["worker", "apps_script"]


@dataclass(slots=True)
class RequestMetadata:
    method: str
    url: str
    payload_size: int
    retry_count: int = 0
    prior_backend_errors: dict[str, int] | None = None
    timeout_budget_ms: int | None = None


class BackendRouter:
    """Selects worker vs apps_script per request using lightweight policy."""

    def __init__(self, config: dict):
        router_cfg = config.get("router", {}) if isinstance(config.get("router"), dict) else {}
        self.enabled = bool(router_cfg.get("enabled", True))
        self.prefer_worker_first = bool(router_cfg.get("prefer_worker_first", True))
        self.worker_payload_limit = int(router_cfg.get("worker_payload_limit", 1024 * 1024 * 2))
        self.worker_retry_threshold = int(router_cfg.get("worker_retry_threshold", 2))
        self.worker_error_threshold = int(router_cfg.get("worker_error_threshold", 3))
        self.timeout_floor_ms = int(router_cfg.get("worker_timeout_floor_ms", 1200))
        self._worker_modes = {"custom_domain", "domain_fronting", "google_fronting"}

    def choose(self, metadata: RequestMetadata, *, worker_mode_available: bool, apps_mode_available: bool) -> BackendName:
        if not self.enabled:
            if apps_mode_available:
                return "apps_script"
            return "worker"

        if not worker_mode_available:
            return "apps_script"
        if not apps_mode_available:
            return "worker"

        if not self.prefer_worker_first:
            return "apps_script"

        if not self._worker_compatible(metadata):
            return "apps_script"

        if self._worker_degraded(metadata):
            return "apps_script"

        return "worker"

    def _worker_compatible(self, metadata: RequestMetadata) -> bool:
        parsed = urlparse(metadata.url)
        if parsed.scheme and parsed.scheme.lower() != "http":
            return False
        if metadata.payload_size > self.worker_payload_limit:
            return False
        return True

    def _worker_degraded(self, metadata: RequestMetadata) -> bool:
        if metadata.retry_count >= self.worker_retry_threshold:
            return True
        if metadata.timeout_budget_ms is not None and metadata.timeout_budget_ms < self.timeout_floor_ms:
            return True
        errors = metadata.prior_backend_errors or {}
        return int(errors.get("worker", 0)) >= self.worker_error_threshold

    def is_worker_mode(self, mode: str) -> bool:
        return mode in self._worker_modes
