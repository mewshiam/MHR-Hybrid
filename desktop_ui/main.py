"""Desktop dashboard UI for MHR Hybrid."""

from __future__ import annotations

import argparse
import sys

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QTabWidget,
    QHBoxLayout,
)

from desktop_ui.api_client import DashboardApiClient, DashboardApiError
from desktop_ui.view_model import DashboardViewModel


class DashboardWindow(QMainWindow):
    def __init__(self, api_base_url: str, poll_seconds: float = 0.0):
        super().__init__()
        self.setWindowTitle("MHR Hybrid Dashboard")
        self.resize(900, 600)

        self.client = DashboardApiClient(base_url=api_base_url)
        self.vm = DashboardViewModel()
        self.tabs: dict[str, tuple[QLabel, QTextEdit]] = {}

        root = QWidget(self)
        layout = QVBoxLayout(root)

        controls = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        controls.addWidget(self.refresh_btn)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.tab_widget = QTabWidget()
        for key, title in self.vm.MODULES.items():
            panel = QWidget()
            p_layout = QVBoxLayout(panel)
            summary = QLabel("-")
            details = QTextEdit()
            details.setReadOnly(True)
            p_layout.addWidget(summary)
            p_layout.addWidget(details)
            self.tab_widget.addTab(panel, title)
            self.tabs[key] = (summary, details)
        layout.addWidget(self.tab_widget)
        self.setCentralWidget(root)

        self._timer = None
        if poll_seconds > 0:
            self._timer = QTimer(self)
            self._timer.setInterval(int(poll_seconds * 1000))
            self._timer.timeout.connect(self.refresh)
            self._timer.start()

        self.refresh()

    def _render(self, states):
        for key, state in states.items():
            summary, details = self.tabs[key]
            summary.setText(f"[{state.status.upper()}] {state.summary}")
            details.setPlainText(state.details)

    def refresh(self):
        self._render(self.vm.loading_state())
        try:
            payload = self.client.fetch_dashboard()
            self._render(self.vm.from_payload(payload))
        except DashboardApiError as exc:
            self._render(self.vm.error_state(exc))
        except Exception as exc:  # defensive catch for UI safety
            self._render(self.vm.error_state(exc))
            QMessageBox.warning(self, "Unexpected error", str(exc))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MHR Hybrid desktop dashboard")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--poll-seconds", type=float, default=0.0, help="0 disables periodic polling")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    app = QApplication(sys.argv)
    win = DashboardWindow(api_base_url=args.api_base_url, poll_seconds=max(0.0, args.poll_seconds))
    win.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
