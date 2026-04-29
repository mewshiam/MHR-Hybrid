#!/usr/bin/env python3
"""
MHR-Hybrid — Bypass DPI censorship via Domain Fronting.

Run a local HTTP proxy that tunnels all traffic through a CDN using
domain fronting: the TLS SNI shows an allowed domain while the encrypted
HTTP Host header routes to your Cloudflare Worker relay.
"""

from src.app import MHRApplication


def main():
    app = MHRApplication()
    app.run_cli()


if __name__ == "__main__":
    main()
