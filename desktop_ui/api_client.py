"""HTTP API client for the MHR dashboard endpoint."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class DashboardApiError(RuntimeError):
    """Raised when dashboard API request fails."""


@dataclass(slots=True)
class DashboardApiClient:
    base_url: str = "http://127.0.0.1:8080"
    timeout_seconds: float = 5.0

    @property
    def dashboard_endpoint(self) -> str:
        return f"{self.base_url.rstrip('/')}/__mhr/api/dashboard"

    def fetch_dashboard(self) -> dict:
        endpoint = self.dashboard_endpoint
        req = Request(endpoint, method="GET")
        try:
            with urlopen(req, timeout=self.timeout_seconds) as resp:
                status = getattr(resp, "status", 200)
                if status != 200:
                    raise DashboardApiError(f"API returned {status}")
                body = resp.read().decode("utf-8")
        except HTTPError as exc:
            raise DashboardApiError(f"API returned {exc.code}") from exc
        except URLError as exc:
            raise DashboardApiError(f"Could not connect to {endpoint}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise DashboardApiError(f"Request timed out after {self.timeout_seconds}s") from exc

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise DashboardApiError("Invalid JSON returned by dashboard API") from exc

        if not isinstance(payload, dict):
            raise DashboardApiError("Dashboard API payload must be a JSON object")
        return payload
