import argparse
import asyncio
import json
import logging
import os
import sys

from src.cert_installer import install_ca, is_ca_trusted
from src.mitm import CA_CERT_FILE
from src.proxy_server import ProxyServer


__version__ = "1.0.0"


def setup_logging(level_name: str):
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)-12s] %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )


class MHRApplication:
    def __init__(self):
        self.args = None
        self.config = None
        self.proxy_server = None
        self.log = logging.getLogger("Main")

    def parse_args(self):
        parser = argparse.ArgumentParser(
            prog="mhr-hybrid",
            description="MHR-Hybrid local HTTP proxy that tunnels traffic through domain fronting.",
        )
        parser.add_argument(
            "-c", "--config",
            default=os.environ.get("DFT_CONFIG", "config.json"),
            help="Path to config file (default: config.json, env: DFT_CONFIG)",
        )
        parser.add_argument(
            "-p", "--port",
            type=int,
            default=None,
            help="Override listen port (env: DFT_PORT)",
        )
        parser.add_argument(
            "--host",
            default=None,
            help="Override listen host (env: DFT_HOST)",
        )
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default=None,
            help="Override log level (env: DFT_LOG_LEVEL)",
        )
        parser.add_argument(
            "-v", "--version",
            action="version",
            version=f"MHR-Hybrid v{__version__}",
        )
        parser.add_argument(
            "--install-cert",
            action="store_true",
            help="Install the MITM CA certificate as a trusted root and exit.",
        )
        parser.add_argument(
            "--no-cert-check",
            action="store_true",
            help="Skip the certificate installation check on startup.",
        )
        self.args = parser.parse_args()
        return self.args

    def load_and_validate_config(self):
        config_path = self.args.config
        try:
            with open(config_path) as f:
                config = json.load(f)
        except FileNotFoundError:
            print(f"Config not found: {config_path}")
            print("Copy config.example.json to config.json and fill in your values.")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in config: {e}")
            sys.exit(1)

        for key in ("auth_key",):
            if key not in config:
                print(f"Missing required config key: {key}")
                sys.exit(1)

        mode = config.get("mode", "domain_fronting")
        if mode == "custom_domain" and "custom_domain" not in config:
            print("Mode 'custom_domain' requires 'custom_domain' in config")
            sys.exit(1)
        if mode == "domain_fronting":
            for key in ("front_domain", "worker_host"):
                if key not in config:
                    print(f"Mode 'domain_fronting' requires '{key}' in config")
                    sys.exit(1)
        if mode == "google_fronting":
            if "worker_host" not in config:
                print("Mode 'google_fronting' requires 'worker_host' in config (your Cloud Run URL)")
                sys.exit(1)
        if mode == "apps_script":
            sid = config.get("script_ids") or config.get("script_id")
            if not sid or (isinstance(sid, str) and sid == "YOUR_APPS_SCRIPT_DEPLOYMENT_ID"):
                print("Mode 'apps_script' requires 'script_id' in config.")
                print("Deploy the Apps Script from appsscript/Code.gs and paste the Deployment ID.")
                sys.exit(1)

        self.config = config
        return self.config

    def apply_overrides(self):
        config = self.config

        if os.environ.get("DFT_AUTH_KEY"):
            config["auth_key"] = os.environ["DFT_AUTH_KEY"]
        if os.environ.get("DFT_SCRIPT_ID"):
            config["script_id"] = os.environ["DFT_SCRIPT_ID"]

        if self.args.port is not None:
            config["listen_port"] = self.args.port
        elif os.environ.get("DFT_PORT"):
            config["listen_port"] = int(os.environ["DFT_PORT"])

        if self.args.host is not None:
            config["listen_host"] = self.args.host
        elif os.environ.get("DFT_HOST"):
            config["listen_host"] = os.environ["DFT_HOST"]

        if self.args.log_level is not None:
            config["log_level"] = self.args.log_level
        elif os.environ.get("DFT_LOG_LEVEL"):
            config["log_level"] = os.environ["DFT_LOG_LEVEL"]

        return config

    def initialize(self):
        if self.args.install_cert:
            setup_logging("INFO")
            _log = logging.getLogger("Main")
            _log.info("Installing CA certificate…")
            ok = install_ca(CA_CERT_FILE)
            sys.exit(0 if ok else 1)

        setup_logging(self.config.get("log_level", "INFO"))
        self.log = logging.getLogger("Main")

        mode = self.config.get("mode", "domain_fronting")
        self.log.info("MHR-Hybrid starting (mode: %s)", mode)

        if mode == "custom_domain":
            self.log.info("Custom domain    : %s", self.config["custom_domain"])
        elif mode == "google_fronting":
            self.log.info("Google fronting   : SNI=%s → Host=%s",
                          self.config.get("front_domain", "www.google.com"), self.config["worker_host"])
            self.log.info("Google IP         : %s", self.config.get("google_ip", "216.239.38.120"))
        elif mode == "apps_script":
            self.log.info("Apps Script relay : SNI=%s → script.google.com",
                          self.config.get("front_domain", "www.google.com"))
            script_ids = self.config.get("script_ids") or self.config.get("script_id")
            if isinstance(script_ids, list):
                self.log.info("Script IDs        : %d scripts (round-robin)", len(script_ids))
                for i, sid in enumerate(script_ids):
                    self.log.info("  [%d] %s", i + 1, sid)
            else:
                self.log.info("Script ID         : %s", script_ids)

            if not os.path.exists(CA_CERT_FILE):
                from src.mitm import MITMCertManager
                MITMCertManager()

            if not self.args.no_cert_check:
                if not is_ca_trusted(CA_CERT_FILE):
                    self.log.warning("MITM CA is not trusted — attempting automatic installation…")
                    ok = install_ca(CA_CERT_FILE)
                    if ok:
                        self.log.info("CA certificate installed. You may need to restart your browser.")
                    else:
                        self.log.error(
                            "Auto-install failed. Run with --install-cert (may need admin/sudo) "
                            "or manually install ca/ca.crt as a trusted root CA."
                        )
                else:
                    self.log.info("MITM CA is already trusted.")
        else:
            self.log.info("Front domain (SNI) : %s", self.config.get("front_domain", "?"))
            self.log.info("Worker host (Host) : %s", self.config.get("worker_host", "?"))

        self.log.info(
            "Proxy address      : %s:%d",
            self.config.get("listen_host", "127.0.0.1"),
            self.config.get("listen_port", 8080),
        )

    async def start(self):
        self.proxy_server = ProxyServer(self.config)
        await self.proxy_server.start()

    async def stop(self):
        if self.proxy_server is not None:
            await self.proxy_server.stop()

    async def run(self):
        try:
            await self.start()
        finally:
            await self.stop()

    def run_cli(self):
        self.parse_args()
        self.load_and_validate_config()
        self.apply_overrides()
        self.initialize()
        try:
            asyncio.run(self.run())
        except KeyboardInterrupt:
            self.log.info("Stopped")

