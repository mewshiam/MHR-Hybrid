"""View-model/controller layer for desktop dashboard widgets."""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(slots=True)
class ModuleViewState:
    status: str
    summary: str
    details: str


class DashboardViewModel:
    MODULES = {
        "backend-status": "Backend status / health",
        "routing-policy": "Routing policy preview",
        "relay-diagnostics": "Relay diagnostics / logs",
        "config-validation": "Config validation",
    }

    def loading_state(self) -> dict[str, ModuleViewState]:
        return {
            key: ModuleViewState(
                status="loading",
                summary="Loading module data...",
                details="Please wait while we query local proxy APIs.",
            )
            for key in self.MODULES
        }

    def error_state(self, err: Exception, endpoint: str | None = None) -> dict[str, ModuleViewState]:
        endpoint_hint = endpoint or "http://127.0.0.1:<port>/__mhr/api/dashboard"
        detail = (
            f"{err}\n"
            f"Action:\n"
            f"1) Start proxy backend on the configured host/port.\n"
            f"2) Verify this endpoint is reachable: {endpoint_hint}\n"
            "3) Check host/port in PyQt dashboard settings and refresh."
        )
        return {
            key: ModuleViewState("error", "Failed to load dashboard data.", detail)
            for key in self.MODULES
        }

    def from_payload(self, data: dict) -> dict[str, ModuleViewState]:
        backends = data.get("backends") or {}
        rows = "\n".join(
            f"{name}: health={backend.get('health')}, errors={backend.get('errors')}, "
            f"circuit_open_until={backend.get('circuit_open_until')}"
            for name, backend in backends.items()
        )
        backend_state = ModuleViewState(
            "success" if rows else "empty",
            "Backend telemetry available." if rows else "No backend telemetry yet.",
            rows or "Action: generate traffic then click Refresh.",
        )

        routing_policy = data.get("routing_policy")
        routing_state = ModuleViewState(
            "success" if routing_policy else "empty",
            "Routing policy loaded." if routing_policy else "No routing policy found.",
            json.dumps(routing_policy, indent=2)
            if routing_policy
            else "Action: verify config mode and restart proxy.",
        )

        diag_lines = "\n".join(data.get("relay_diagnostics") or [])
        diag_state = ModuleViewState(
            "success" if diag_lines else "empty",
            "Recent diagnostics fetched." if diag_lines else "No relay diagnostics yet.",
            diag_lines or "Action: make at least one request through proxy.",
        )

        cfg = data.get("config_validation") or {}
        cfg_ok = bool(cfg.get("valid"))
        cfg_state = ModuleViewState(
            "success" if cfg_ok else "error",
            "Config validation passed." if cfg_ok else "Config validation failed.",
            json.dumps(cfg if cfg else {"errors": ["Unknown validation error"]}, indent=2),
        )

        return {
            "backend-status": backend_state,
            "routing-policy": routing_state,
            "relay-diagnostics": diag_state,
            "config-validation": cfg_state,
        }
