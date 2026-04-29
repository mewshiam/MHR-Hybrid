#!/usr/bin/env python3
"""
MHR-Hybrid — Bypass DPI censorship via Domain Fronting.

Run a local HTTP proxy that tunnels all traffic through a CDN using
domain fronting: the TLS SNI shows an allowed domain while the encrypted
HTTP Host header routes to your Cloudflare Worker relay.
"""

import sys


def main():
    try:
        from src.app import MHRApplication
    except ModuleNotFoundError as exc:
        print(f"[X] Missing Python dependency: {exc.name}", file=sys.stderr)
        print("    Run pip install -r requirements.txt", file=sys.stderr)
        raise SystemExit(1)

    app = MHRApplication()
    app.run_cli()


if __name__ == "__main__":
    main()
