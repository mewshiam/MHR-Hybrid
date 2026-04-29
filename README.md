# MHR-Hybrid

[![GitHub](https://img.shields.io/badge/GitHub-MHR--Hybrid-blue?logo=github)](https://github.com/mewshiam/MHR-Hybrid)

| [English](README.md) | [Persian](README_FA.md) |
| :---: | :---: |

## 1) Overview

MHR-Hybrid runs a **local proxy backend** and can optionally expose a local web dashboard endpoint plus a separate **PyQt desktop dashboard**.

### Architecture flow

```text
Browser / App Client
        |
        v
Local MHR-Hybrid Proxy Backend (main.py)
        |
        +--> Relay backend(s):
              - Google Apps Script relay (`mode: apps_script`)
              - Google fronting relay (`mode: google_fronting`)
              - Domain-fronted worker relay (`mode: domain_fronting`)
              - Direct custom-domain worker relay (`mode: custom_domain`)

Separate process:
PyQt Desktop Dashboard (desktop_ui/main.py)
   -> reads backend API: GET http://<host>:<port>/__mhr/api/dashboard
```

### What changed vs the old web UI

- The legacy `ui/` web dashboard is now **optional/deprecated** for day-to-day use.
- The recommended local operator interface is the **PyQt desktop dashboard** (`python -m desktop_ui.main`).
- The embedded web route (`/__mhr/ui/`) remains available for compatibility, but it is no longer the primary UX.

---

## 2) Quickstart (no virtualenv required)

1. Install **Python 3.10+** and ensure it is available on your PATH as `python` (Windows) or `python3` (Linux/macOS).
2. Install dependencies:
   - Windows:
   ```powershell
   pip install -r requirements.txt
   ```
   - Linux/macOS:
   ```bash
   pip install -r requirements.txt
   ```
3. Create config:
   - Windows:
   ```powershell
   Copy-Item config.example.json config.json
   ```
   - Linux/macOS:
   ```bash
   cp config.example.json config.json
   ```
4. Run launcher:
   - Windows: `run.bat`
   - Linux/macOS: `./run.sh`

The launchers also try to auto-install missing dependencies on first run.

## 3) Optional: recommended isolation with virtualenv

If you prefer isolated Python packages, use a virtual environment:

**Windows (PowerShell):**
```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux/macOS (bash/zsh):**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If your network cannot reach PyPI directly:
```bash
pip install -r requirements.txt -i https://mirror-pypi.runflare.com/simple/ --trusted-host mirror-pypi.runflare.com
```

---

## 4) Configuration (`config.json`)

Create your local config file first:

**Windows (PowerShell):**
```powershell
Copy-Item config.example.json config.json
```

**Linux/macOS:**
```bash
cp config.example.json config.json
```

### 4.1 Minimal example

```json
{
  "mode": "apps_script",
  "google_ip": "216.239.38.120",
  "front_domain": "www.google.com",
  "script_id": "YOUR_APPS_SCRIPT_DEPLOYMENT_ID",
  "auth_key": "CHANGE_ME_TO_A_STRONG_SECRET",
  "listen_host": "127.0.0.1",
  "listen_port": 8085,
  "log_level": "INFO",
  "verify_ssl": true
}
```

### 4.2 Key reference (purpose, type/values, default behavior, example)

#### Core keys

- `mode`
  - Purpose: Select relay strategy.
  - Type/allowed: string; one of `apps_script`, `google_fronting`, `domain_fronting`, `custom_domain`.
  - Default behavior: If omitted, runtime treats mode like `domain_fronting`.
  - Example: `"mode": "apps_script"`

- `auth_key`
  - Purpose: Shared auth secret for relay contract.
  - Type/allowed: non-empty string.
  - Default behavior: required; startup fails if missing.
  - Example: `"auth_key": "my-strong-secret"`

- `listen_host`
  - Purpose: Bind address for local proxy/API.
  - Type/allowed: string IP/host.
  - Default behavior: `127.0.0.1`.
  - Example: `"listen_host": "127.0.0.1"`

- `listen_port`
  - Purpose: TCP listen port for local proxy/API.
  - Type/allowed: integer.
  - Default behavior: backend defaults to `8080` if not set.
  - Example: `"listen_port": 8085`

- `log_level`
  - Purpose: Logging verbosity.
  - Type/allowed: `DEBUG`, `INFO`, `WARNING`, `ERROR`.
  - Default behavior: `INFO`.
  - Example: `"log_level": "DEBUG"`

- `verify_ssl`
  - Purpose: Upstream TLS verification behavior.
  - Type/allowed: boolean.
  - Default behavior: `true` if omitted in example flow.
  - Example: `"verify_ssl": true`

#### Mode-specific keys

- `apps_script` mode keys
  - `script_id` (string) or `script_ids` (array of strings)
    - Purpose: Apps Script deployment ID(s), optional round-robin when list provided.
    - Default behavior: required in this mode; startup fails without valid value.
    - Example: `"script_id": "AKfycbx..."`

- `google_fronting` mode keys
  - `worker_host` (string)
    - Purpose: Upstream worker/Cloud Run host used behind Google front.
    - Default behavior: required in this mode.
    - Example: `"worker_host": "my-service.a.run.app"`
  - `google_ip` / `front_domain`
    - Purpose: Google-facing front target details.
    - Default behavior: if omitted, runtime logs default front domain as `www.google.com` and common Google IP usage.
    - Example: `"front_domain": "www.google.com"`

- `domain_fronting` mode keys
  - `front_domain` (string), `worker_host` (string)
    - Purpose: SNI/front host and effective upstream host.
    - Default behavior: both required in this mode.
    - Example:
      ```json
      { "front_domain": "www.google.com", "worker_host": "myworker.workers.dev" }
      ```

- `custom_domain` mode key
  - `custom_domain` (string)
    - Purpose: Use your own domain endpoint routing.
    - Default behavior: required in this mode.
    - Example: `"custom_domain": "relay.example.com"`

#### Frequently used optional keys

- `socks5_enabled` (bool, default `true`), `socks5_host` (string), `socks5_port` (int, default `1080`)
- `hosts` (object map of host/suffix overrides to IPs)
- `router` (object)
  - `enabled` (bool, default `true`)
  - `prefer_worker_first` (bool, default `true`)
  - `worker_payload_limit` (int bytes, default `2097152`)
  - `worker_retry_threshold` (int, default `2`)
  - `worker_error_threshold` (int, default `3`)
  - `worker_timeout_floor_ms` (int, default `1200`)

---

## 5) Certificate setup

> Certificate trust is most relevant when using interception flows (notably `apps_script`).

### 5.1 Automatic installation

Run installer mode:

```bash
python main.py --install-cert
```

This installs the generated CA certificate into supported trust stores, then exits.

### 5.2 Manual installation

Certificate file path used by the project:

```text
ca/ca.crt
```

Manual install targets:
- Windows: Trusted Root Certification Authorities (Current User or Local Machine)
- macOS: login keychain or system keychain
- Linux: distro trust store (`update-ca-certificates`, `update-ca-trust`, or `trust extract-compat`)
- Firefox/NSS stores when present

### 5.3 Verify certificate trust

Start backend without skipping checks:

```bash
python main.py --config config.json
```

Expected success signal in logs:
- `MITM CA is already trusted.`

### 5.4 Rollback (remove trust)

Remove the installed `MHR-Hybrid` root CA from your OS/browser trust store using platform certificate manager tools.

After rollback, restart the browser and backend; HTTPS interception paths should no longer be trusted.

---

## 6) Run backend service

### 6.1 CLI usage

```bash
python main.py [--config PATH] [--host HOST] [--port PORT] [--log-level LEVEL] [--install-cert] [--no-cert-check]
```

### 6.2 Common examples

- Use explicit config file:
  ```bash
  python main.py --config config.json
  ```
- Bind custom interface/port:
  ```bash
  python main.py --host 127.0.0.1 --port 8085
  ```
- Verbose debug logs:
  ```bash
  python main.py --log-level DEBUG
  ```
- Certificate bootstrap only:
  ```bash
  python main.py --install-cert
  ```
- Skip startup trust verification (advanced/debug only):
  ```bash
  python main.py --no-cert-check
  ```

### 6.3 Expected startup logs and success criteria

Successful startup usually includes:
- Mode banner (for example `MHR-Hybrid starting (mode: apps_script)`).
- Mode-specific routing info (script IDs or host mappings).
- Proxy bind line (`Proxy address      : <host>:<port>`).

Success criteria:
- Process remains running.
- Config validation passes (no missing mode-required keys).
- Local endpoint is reachable at configured host/port.

---

## 7) Run PyQt desktop UI

### 7.1 Launch commands

- Target host/port:
  ```bash
  python -m desktop_ui.main --host 127.0.0.1 --port 8085
  ```
- Or pass full API base URL:
  ```bash
  python -m desktop_ui.main --api-base-url http://127.0.0.1:8085
  ```
- Optional periodic refresh:
  ```bash
  python -m desktop_ui.main --host 127.0.0.1 --port 8085 --poll-seconds 5
  ```

### 7.2 Refresh behavior

- Manual refresh: **Refresh** button.
- Automatic refresh: enabled only if `--poll-seconds > 0`.

### 7.3 Backend unreachable error states

If backend API is unreachable, dashboard modules move into error state and show actionable guidance (start/check backend, verify host/port/API URL).

---

## 8) Daily usage guides

### 8.1 Configure browser proxy

Manual browser proxy values:
- HTTP proxy host: `127.0.0.1`
- HTTP proxy port: your `listen_port` (for example `8085`)

Optional extension workflow:
- Install FoxyProxy (Chrome or Firefox).
- Add a profile pointing to `127.0.0.1:<listen_port>`.
- Enable profile before browsing test targets.

### 8.2 Traffic validation procedure

1. Start backend and ensure no startup config/cert errors.
2. Enable browser proxy profile.
3. Open a validation site (for example `https://ipleak.net`).
4. Confirm traffic egress matches expected relay/provider behavior.
5. Check backend logs for relay activity and status summaries.

### 8.3 Interpreting dashboard modules

- **Backend status / health**: confirms API connectivity/runtime health.
- **Routing policy preview**: shows worker/apps-script routing decisions.
- **Relay diagnostics / log summaries**: surfaces upstream response patterns.
- **Config validation**: highlights missing or invalid settings.

---


## 9) Operational runbook

### 9.1 First-time setup checklist

Use this checklist for a clean initial deployment:

1. **Install dependencies**
   - Create and activate `.venv`.
   - Install packages with `pip install -r requirements.txt`.
2. **Configure runtime**
   - Copy `config.example.json` to `config.json`.
   - Set required keys for your selected mode (`mode`, `auth_key`, plus mode-specific fields).
3. **Install/trust certificate** (when interception mode is used)
   - Run `python main.py --install-cert`.
   - Confirm `ca/ca.crt` is trusted in your OS/browser trust store.
4. **First backend run**
   - Start backend with `python main.py --config config.json`.
   - Verify startup logs show bind address and no config/certificate errors.
5. **UI verification**
   - Launch desktop UI: `python -m desktop_ui.main --host 127.0.0.1 --port <listen_port>`.
   - Confirm dashboard modules load without backend/API error states.

### 9.2 Normal operation

#### Start/stop backend safely

- **Start**
  ```bash
  python main.py --config config.json
  ```
- **Stop**
  - Use `Ctrl+C` in the terminal running backend.
  - Wait for process exit before restarting on the same port.
- **Safe restart sequence**
  1. Stop backend cleanly (`Ctrl+C`).
  2. Confirm port is free (for example with `ss -ltnp` on Linux/macOS or `netstat -ano` on Windows).
  3. Start backend again with explicit config.

#### Start/stop desktop UI

- **Start**
  ```bash
  python -m desktop_ui.main --host 127.0.0.1 --port <listen_port>
  ```
- **Stop**
  - Close the desktop window, or terminate process from terminal (`Ctrl+C` if launched interactively).

#### Verify proxy behavior and dashboard health

1. Enable browser proxy to `127.0.0.1:<listen_port>`.
2. Open a test endpoint such as `https://ipleak.net`.
3. Confirm expected egress behavior.
4. In dashboard, verify backend health is green/reachable and no API error banners appear.

### 9.3 Maintenance

#### Updating repo and dependencies

1. Pull latest changes:
   ```bash
   git pull --rebase
   ```
2. Reactivate `.venv` and update dependencies:
   ```bash
   pip install -r requirements.txt --upgrade
   ```
3. Compare `config.example.json` to your `config.json` and merge any new required keys.
4. Restart backend and desktop UI after updates.

#### Rotating auth key and updating config

1. Generate a new strong random secret.
2. Update `auth_key` in `config.json`.
3. Update the corresponding secret in your relay backend(s).
4. Restart backend and validate requests succeed (no auth mismatch errors).

#### Renewing/reinstalling certificates

- Re-run installer workflow:
  ```bash
  python main.py --install-cert
  ```
- Restart browser and backend.
- Re-verify trust via startup logs (`MITM CA is already trusted.`).

### 9.4 Observability

#### Where logs appear

- Backend logs print to the terminal/session where `python main.py ...` is running.
- Desktop UI diagnostics appear in the terminal/session used to start `python -m desktop_ui.main ...`.

#### Recommended log levels

- **Normal operation:** `INFO`
- **Investigation/debug sessions:** `DEBUG`
- You can set level via `config.json` (`log_level`) or CLI `--log-level`.

#### Capture diagnostics for bug reports

1. Start backend with debug logging:
   ```bash
   python main.py --config config.json --log-level DEBUG
   ```
2. Reproduce issue with timestamps noted.
3. Capture:
   - Backend terminal logs.
   - Desktop UI terminal logs (if UI-related).
   - Sanitized `config.json` (redact `auth_key` and sensitive hosts if needed).
4. Include OS, Python version, selected `mode`, and exact command lines used.

### 9.5 Recovery procedures

#### Reset to known-good config

1. Stop backend/UI.
2. Backup current config:
   ```bash
   cp config.json config.json.bak
   ```
3. Restore baseline:
   ```bash
   cp config.example.json config.json
   ```
4. Re-apply required environment-specific values (`auth_key`, relay identifiers/domains, ports).
5. Start backend and validate health from dashboard/API.

#### Port collision recovery

1. Identify conflicting process on target port (`listen_port` / `socks5_port`).
2. Stop conflicting process or change MHR-Hybrid ports in `config.json`.
3. Restart backend and confirm bind succeeds.

#### Certificate uninstall/reinstall flow

1. Remove `MHR-Hybrid` CA from OS/browser trust store.
2. Restart browser to clear trust cache.
3. Reinstall certificate:
   ```bash
   python main.py --install-cert
   ```
4. Restart backend and verify trust success log.

### 9.6 Uninstall/cleanup

#### Remove venv/dependencies

- From repository root, delete virtual environment folder:
  - Linux/macOS: `rm -rf .venv`
  - Windows (PowerShell): `Remove-Item -Recurse -Force .venv`

#### Remove generated cert artifacts and temporary files

- Remove project-generated certificate artifacts (if present), such as files under `ca/` created by local setup.
- Remove temporary local logs/artifacts you created during debugging.
- Optionally remove cloned repository directory once no longer needed.

---

## 10) Troubleshooting matrix

| Symptom | Probable cause | Fix |
|---|---|---|
| Browser cert warning / HTTPS fails | Local MITM CA not trusted | Run `python main.py --install-cert`, restart browser, verify trust logs. |
| `Address already in use` | Port conflict on `listen_port` or `socks5_port` | Change port(s) in `config.json` or CLI `--port`; ensure socks and proxy ports differ on same host. |
| Startup says missing config key | Invalid/incomplete `config.json` for chosen mode | Recheck required keys (`auth_key`, plus mode-specific fields). |
| Relay returns auth or quota-like errors | `auth_key` mismatch or relay-side throttling | Sync secret on both ends; rotate key; inspect relay logs/status. |
| Desktop UI shows API error state | Backend not running or wrong host/port | Start backend first; verify `--host/--port` or `--api-base-url` in desktop launch command. |

---

## 11) Security and safety

- This project is for **educational/testing/research** use.
- Running local MITM interception changes TLS trust on your system.
- Misconfiguration can expose sensitive traffic or break normal browsing.
- You are responsible for legal/policy compliance in your jurisdiction and service-provider terms.
- Use isolated test environments (VM, non-primary browser profile, dedicated accounts) before production-like usage.

---

## 12) Developer notes

### 12.1 File layout (backend/UI)

- `main.py` → CLI entrypoint.
- `src/app.py` → argument parsing, config validation, startup orchestration.
- `src/proxy/server.py` → local proxy runtime.
- `src/domain_fronter.py` / `src/backend_adapters.py` / `src/backend_router.py` → relay transport, adapters, and backend selection policy.
- `src/cert_installer.py` → cross-platform trust install/check.
- `desktop_ui/main.py` + `desktop_ui/*` → PyQt dashboard app.
- `ui/*` → legacy web UI assets (compatibility path).
- `config.example.json` → baseline config template.

### 12.2 Add a new backend mode

1. Define config contract and validation in `src/app.py`.
2. Add relay transport/adapter behavior (`src/backend_adapters.py` and/or `src/domain_fronter.py`).
3. Update backend selection policy if needed (`src/backend_router.py`).
4. Expose telemetry fields expected by dashboard API.
5. Document new mode keys in this README and `config.example.json`.

### 12.3 Add a new dashboard panel

1. Add module definition in `desktop_ui/view_model.py`.
2. Map new API payload segment to panel state.
3. Ensure backend endpoint (`/__mhr/api/dashboard`) includes required fields.
4. Add rendering details in PyQt view if custom display logic is needed.

---

## Disclaimer

`MHR-Hybrid` is provided without warranty for educational, testing, and research purposes. You are solely responsible for deployment, configuration, legal compliance, and operational safety.
