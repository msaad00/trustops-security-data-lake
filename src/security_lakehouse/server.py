"""Lightweight human and agent API for the assessment engine."""

from __future__ import annotations

import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from security_lakehouse import api_legacy, api_v1
from security_lakehouse.dashboard import render_dashboard
from security_lakehouse.data_policy import redact_payload
from security_lakehouse.io import resolve_path
from security_lakehouse.web import web_dist_dir, web_dist_index

AUDITOR_ROLE = "auditor"


def serve(lake_dir: str | Path, *, host: str = "127.0.0.1", port: int = 8787) -> None:
    """Serve the TrustOps console and JSON assessment API."""
    lake = resolve_path(lake_dir)
    dashboard = lake / "console.html"
    render_dashboard(lake, dashboard)

    class Handler(_Handler):
        lake_dir = lake
        dashboard_path = dashboard
        web_dist = web_dist_dir() if web_dist_index() else None

    httpd = ThreadingHTTPServer((host, port), Handler)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()


# MIME types Next.js static export ships that aren't always in the system table.
_MIME_OVERRIDES = {
    ".mjs": "text/javascript",
    ".map": "application/json",
    ".webmanifest": "application/manifest+json",
}


class _Handler(BaseHTTPRequestHandler):
    lake_dir: Path
    dashboard_path: Path
    web_dist: Path | None = None

    server_version = "TrustOpsAssessment/0.1"

    @staticmethod
    def _safe_header_value(value: str) -> str:
        """Return a header-safe value by removing CR/LF characters."""
        return str(value).replace("\r", "").replace("\n", "")

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if self.web_dist is not None and self._serve_from_dist(parsed.path):
            return
        if parsed.path in {"/", "/console", "/console/"}:
            self._send_bytes(self.dashboard_path.read_bytes(), content_type="text/html; charset=utf-8")
            return
        if parsed.path == "/api/healthz":
            self._send_json({"ok": True, "service": "trustops-assessment"})
            return
        if parsed.path == "/api/v1/connectors/aws-posture/link/template.yaml":
            from security_lakehouse.cloud_linking import aws_template_bytes

            self._send_bytes(aws_template_bytes(), content_type="application/x-yaml")
            return
        if parsed.path.startswith("/api/v1/connectors/azure-posture/link/callback"):
            self._handle_azure_link_callback(parse_qs(parsed.query))
            return
        if parsed.path == "/api/v1" or parsed.path.startswith("/api/v1/"):
            self._handle_v1_get(parsed.path, parse_qs(parsed.query))
            return
        status, body = api_legacy.handle_get(parsed.path, parse_qs(parsed.query), self.lake_dir)
        self._send_json(body, status=status)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/v1/"):
            if self._role() == AUDITOR_ROLE:
                self._send_json(
                    {"error": "forbidden", "reason": "auditor role is read-only"}, status=HTTPStatus.FORBIDDEN
                )
                return
            self._handle_v1_post(parsed.path)
            return
        request_body = self._read_json_body()
        if self.headers.get("Idempotency-Key") and "idempotency_key" not in request_body:
            request_body = {**request_body, "idempotency_key": self.headers["Idempotency-Key"]}
        status, body = api_legacy.handle_post(parsed.path, request_body, self.lake_dir, role=self._role())
        self._send_json(body, status=status)

    def _handle_azure_link_callback(self, query: dict[str, list[str]]) -> None:
        from security_lakehouse.cloud_linking import (
            azure_callback_redirect,
            get_cloud_link_session,
            normalize_link_session_id,
            record_azure_consent,
        )
        from security_lakehouse.public_url import normalize_public_url

        session_id = normalize_link_session_id((query.get("state") or [""])[0])
        azure_tenant = (query.get("tenant") or [""])[0].strip()
        admin_consent = (query.get("admin_consent") or [""])[0]
        public_url = normalize_public_url(os.environ.get("TRUSTOPS_PUBLIC_URL"))
        if not session_id or get_cloud_link_session(self.lake_dir, session_id) is None:
            self._send_json(
                api_v1.error_envelope("bad_request", "invalid cloud link session", resource="connector.link.callback"),
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        consented = str(admin_consent).lower() in {"true", "1", "yes"}
        record_azure_consent(
            self.lake_dir,
            session_id=session_id,
            azure_tenant_id=azure_tenant or "unknown",
            admin_consent=consented,
        )
        location = azure_callback_redirect(session_id=session_id, public_url=public_url)
        self.send_response(int(HTTPStatus.FOUND))
        self.send_header("location", self._safe_header_value(location))
        self.send_header("cache-control", "no-store")
        self.end_headers()

    def _handle_v1_get(self, path: str, query: dict[str, list[str]]) -> None:
        """Versioned API surface for headless clients.

        The legacy `/api/*` routes remain UI-compatible. `/api/v1/*` wraps
        resources in a stable envelope and applies common collection controls.
        The contract itself lives in :mod:`security_lakehouse.api_v1` so the
        stdlib server and the optional FastAPI server stay byte-for-byte equal.
        """
        export_prefix = "/api/v1/snapshots/"
        if path.endswith("/export.pdf") and path.startswith(export_prefix):
            snapshot_id = path[len(export_prefix) : -len("/export.pdf")]
            self._handle_snapshot_pdf_export(snapshot_id)
            return
        status, body = api_v1.handle_get(path, query, self.lake_dir)
        self._send_json(body, status=status)

    def _handle_snapshot_pdf_export(self, snapshot_id: str) -> None:
        from security_lakehouse.assessment import load_snapshot
        from security_lakehouse.reporting.executive_pdf import render_executive_pdf

        try:
            assessment = load_snapshot(self.lake_dir, snapshot_id)
            pdf_bytes = render_executive_pdf(assessment)
        except FileNotFoundError:
            self._send_json(
                api_v1.error_envelope("not_found", "snapshot not found", resource="snapshots.export"),
                status=HTTPStatus.NOT_FOUND,
            )
            return
        except RuntimeError as exc:
            self._send_json(
                api_v1.error_envelope("not_implemented", str(exc), resource="snapshots.export"),
                status=HTTPStatus.NOT_IMPLEMENTED,
            )
            return
        from security_lakehouse.assessment import safe_snapshot_export_filename

        self._send_bytes(
            pdf_bytes,
            content_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_snapshot_export_filename(snapshot_id)}"',
            },
        )

    def _handle_v1_post(self, path: str) -> None:
        body = self._read_json_body()
        status, payload = api_v1.handle_post(path, body, self.lake_dir)
        self._send_json(payload, status=status)

    def _role(self) -> str:
        return (self.headers.get("X-Trust-Role") or "").strip().lower()

    def _redact(self, payload: object) -> object:
        return redact_payload(payload, role=self._role() or "admin")

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _serve_from_dist(self, request_path: str) -> bool:
        """Serve Next.js static export files when the React bundle is packaged.

        Routes resolve in this order:
          - /                                     -> dist/index.html (redirects to /console/dashboard/)
          - /console, /console/                   -> dist/index.html
          - /console/<route>/                     -> dist/<route>/index.html
          - /console/_next/static/<asset>         -> dist/_next/static/<asset>
          - any other /console/<asset>            -> dist/<asset>

        Returns True if the request was handled (200 or 404 served from dist).
        """
        dist = self.web_dist
        if dist is None:
            return False
        if request_path in {"/", "/console", "/console/"}:
            self._send_file(dist / "index.html", "text/html; charset=utf-8")
            return True
        if not request_path.startswith("/console/"):
            return False
        rel = request_path[len("/console/") :]
        # Strip query/fragment if any survived urlparse path handling.
        rel = rel.split("?", 1)[0].split("#", 1)[0]
        candidates: list[Path] = []
        # Treat directory-style routes as <route>/index.html.
        if rel.endswith("/") or not Path(rel).suffix:
            base = rel.rstrip("/")
            if base:
                candidates.append(dist / base / "index.html")
            candidates.append(dist / "index.html")
        if rel:
            candidates.append(dist / rel)
        for candidate in candidates:
            resolved = candidate.resolve()
            try:
                resolved.relative_to(dist.resolve())
            except ValueError:
                continue
            if resolved.is_file():
                content_type = (
                    _MIME_OVERRIDES.get(resolved.suffix)
                    or mimetypes.guess_type(resolved.name)[0]
                    or "application/octet-stream"
                )
                if content_type.startswith("text/") or content_type.endswith("javascript"):
                    content_type = f"{content_type}; charset=utf-8"
                self._send_file(resolved, content_type)
                return True
        return False

    def _send_file(self, path: Path, content_type: str) -> None:
        self._send_bytes(path.read_bytes(), content_type=content_type)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("content-length") or "0")
        if length <= 0:
            return {}
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _send_json(self, payload: object, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(self._redact(payload), indent=2, sort_keys=True, default=str).encode("utf-8")
        self._send_bytes(body, status=status, content_type="application/json; charset=utf-8")

    def _send_bytes(
        self,
        body: bytes,
        *,
        status: HTTPStatus = HTTPStatus.OK,
        content_type: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(int(status))
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        self.send_header("x-content-type-options", "nosniff")
        self.send_header("access-control-allow-origin", "http://127.0.0.1")
        if headers:
            for key, value in headers.items():
                safe_key = key.replace("\r", "").replace("\n", "")
                safe_value = value.replace("\r", "").replace("\n", "")
                self.send_header(safe_key, safe_value)
        self.end_headers()
        self.wfile.write(body)
