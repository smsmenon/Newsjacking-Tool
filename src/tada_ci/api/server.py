from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from tada_ci.services.repository import JsonRepository
from tada_ci.services.reports import build_weekly_report
from tada_ci.services.review import create_review_event
from tada_ci.services.emailer import send_digest_email
from tada_ci.services.content_generator import enrich_signals
from tada_ci.services.theme_manager import load_all_themes, add_theme, update_theme, delete_theme, toggle_theme
from tada_ci.services.discovery_pipeline import run_discovery_pipeline as run_discovery
from tada_ci.services.discovery_emailer import send_discovery_email
from tada_ci.services.contrarian_pipeline import run_contrarian_pipeline


class TadaHandler(SimpleHTTPRequestHandler):
    repo: JsonRepository
    static_root: Path

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        if parsed.path == "/":
            return str(self.static_root / "index.html")
        return str(self.static_root / parsed.path.lstrip("/"))

    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def send_json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json({"status": "healthy", "service": "tada-content-intelligence"})
        elif path == "/api/sources":
            self.send_json({"sources": self.repo.get_sources()})
        elif path == "/api/digest":
            self.send_json(self.repo.get_digest())
        elif path == "/api/signals":
            self.send_json({"signals": self.repo.get_signals()})
        elif path == "/api/review-events":
            self.send_json({"events": self.repo.get_review_events()})
        elif path == "/api/reports/weekly":
            self.send_json(build_weekly_report(self.repo.get_digest()))
        elif path == "/api/themes":
            from tada_ci.services.theme_manager import load_all_themes
            themes = load_all_themes(self.repo.root)
            self.send_json({"themes": themes})
        elif path == "/api/linkedin-profiles":
            import json as _json
            p = self.repo.root / "config" / "linkedin_profiles.json"
            profiles = _json.loads(p.read_text()) if p.exists() else []
            self.send_json({"profiles": profiles})
        elif path == "/api/engagement-config":
            import json as _json
            p = self.repo.root / "config" / "engagement_config.json"
            cfg = _json.loads(p.read_text()) if p.exists() else {}
            self.send_json(cfg)
        else:
            super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/ingestion/run":
                self.send_json(self.repo.refresh_digest())
            elif path == "/api/ingestion/live":
                self.send_json(self.repo.refresh_live_digest())
            elif path == "/api/review-events":
                event = create_review_event(self.read_body())
                self.send_json(self.repo.append_review_event(event), HTTPStatus.CREATED)
            elif path == "/api/email/digest":
                body = self.read_body()
                to_email = body.get("to")
                if not to_email:
                    self.send_json({"error": "missing 'to' field"}, HTTPStatus.BAD_REQUEST)
                    return
                digest = self.repo.get_digest()
                result = send_digest_email(
                    digest,
                    to_email,
                    recipient_name=body.get("recipient_name", "Team"),
                    sender_name=body.get("sender_name", "TADA Intelligence"),
                    cc=body.get("cc"),
                )
                self.send_json(result)
            elif path == "/api/themes":
                body = self.read_body()
                from tada_ci.services.theme_manager import add_theme
                t = add_theme(self.repo.root, body.get("name",""), body.get("description",""), body.get("priority","medium"))
                self.send_json(t, HTTPStatus.CREATED)
            elif path.startswith("/api/themes/") and path.endswith("/toggle"):
                theme_id = path.split("/")[3]
                from tada_ci.services.theme_manager import toggle_theme
                t = toggle_theme(self.repo.root, theme_id)
                self.send_json(t)
            elif path == "/api/sources":
                import json as _json, re as _re
                body = self.read_body()
                name = body.get("name", "").strip()
                url = body.get("url", "").strip()
                if not name or not url:
                    self.send_json({"error": "name and url are required"}, HTTPStatus.BAD_REQUEST)
                    return
                p = self.repo.root / "config" / "sources.json"
                sources = _json.loads(p.read_text()) if p.exists() else []
                new_src = {
                    "name": name, "url": url,
                    "rss_url": url if "rss" in url.lower() or "feed" in url.lower() or "xml" in url.lower() else url,
                    "category": body.get("category", "Custom"),
                    "access_method": "rss", "priority": "medium",
                    "trust_tier": 2, "health_status": "healthy",
                    "enabled": True,
                }
                sources.append(new_src)
                p.write_text(_json.dumps(sources, indent=2))
                self.send_json(new_src, HTTPStatus.CREATED)
            elif path == "/api/linkedin-profiles":
                import json as _json
                body = self.read_body()
                name = body.get("name", "").strip()
                url_or_username = body.get("url", "").strip()
                if not name or not url_or_username:
                    self.send_json({"error": "name and url are required"}, HTTPStatus.BAD_REQUEST)
                    return
                # Extract username from URL if full URL given
                username = url_or_username.rstrip("/").split("/")[-1] if "/" in url_or_username else url_or_username
                p = self.repo.root / "config" / "linkedin_profiles.json"
                profiles = _json.loads(p.read_text()) if p.exists() else []
                new_profile = {"username": username, "name": name, "role": body.get("role", "")}
                profiles.append(new_profile)
                p.write_text(_json.dumps(profiles, indent=2))
                self.send_json(new_profile, HTTPStatus.CREATED)
            elif path == "/api/contrarian/run":
                result = run_contrarian_pipeline(self.repo.root)
                self.send_json(result)
            elif path == "/api/engagement-config":
                import json as _json
                body = self.read_body()
                p = self.repo.root / "config" / "engagement_config.json"
                cfg = _json.loads(p.read_text()) if p.exists() else {}
                linkedin = cfg.get("linkedin", {})
                linkedin.update({k: v for k, v in body.items() if k in ("min_likes", "min_comments", "max_age_hours")})
                cfg["linkedin"] = linkedin
                p.write_text(_json.dumps(cfg, indent=2))
                self.send_json(cfg)
            elif path == "/api/discovery/run":
                sources = self.repo.get_sources()
                result = run_discovery(self.repo.root, sources)
                self.send_json(result)
            elif path == "/api/discovery/email":
                body = self.read_body()
                sources = self.repo.get_sources()
                result = run_discovery(self.repo.root, sources)
                if not result.get("top_articles"):
                    self.send_json({"success": False, "reason": "no_relevant_articles_found", "usage_stats": result.get("usage_stats", {})})
                    return
                email_result = send_discovery_email(
                    result,
                    to_email=body.get("to", ""),
                    recipient_name=body.get("recipient_name", "Team"),
                    sender_name=body.get("sender_name", "TADA Intelligence"),
                )
                email_result["usage_stats"] = result.get("usage_stats", {})
                self.send_json(email_result)
            else:
                self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_PUT(self) -> None:
        path = urlparse(self.path).path
        try:
            if path.startswith("/api/themes/"):
                theme_id = path.split("/")[3]
                body = self.read_body()
                from tada_ci.services.theme_manager import update_theme
                t = update_theme(self.repo.root, theme_id, **body)
                self.send_json(t)
            else:
                self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        try:
            if path.startswith("/api/themes/"):
                theme_id = path.split("/")[3]
                from tada_ci.services.theme_manager import delete_theme
                ok = delete_theme(self.repo.root, theme_id)
                self.send_json({"deleted": ok})
            elif path.startswith("/api/sources/"):
                import json as _json
                idx = int(path.split("/")[3])
                p = self.repo.root / "config" / "sources.json"
                sources = _json.loads(p.read_text()) if p.exists() else []
                if 0 <= idx < len(sources):
                    sources.pop(idx)
                    p.write_text(_json.dumps(sources, indent=2))
                    self.send_json({"deleted": True})
                else:
                    self.send_json({"error": "index out of range"}, HTTPStatus.NOT_FOUND)
            elif path.startswith("/api/linkedin-profiles/"):
                import json as _json
                idx = int(path.split("/")[3])
                p = self.repo.root / "config" / "linkedin_profiles.json"
                profiles = _json.loads(p.read_text()) if p.exists() else []
                if 0 <= idx < len(profiles):
                    profiles.pop(idx)
                    p.write_text(_json.dumps(profiles, indent=2))
                    self.send_json({"deleted": True})
                else:
                    self.send_json({"error": "index out of range"}, HTTPStatus.NOT_FOUND)
            else:
                self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except (ValueError, IndexError) as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def run_server(root: Path, host: str, port: int) -> None:
    TadaHandler.repo = JsonRepository(root)
    TadaHandler.static_root = root / "dashboard"
    server = ThreadingHTTPServer((host, port), TadaHandler)
    print(f"TADA Content Intelligence running at http://{host}:{port}")
    server.serve_forever()


def _load_dotenv(root: Path) -> None:
    env_file = root / ".env"
    if not env_file.exists():
        return
    import os
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip())


def main() -> None:
    import os
    parser = argparse.ArgumentParser(description="Run local TADA API and dashboard.")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[3], type=Path)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=int(os.environ.get("PORT", 8787)), type=int)
    args = parser.parse_args()
    root = args.root.resolve()
    _load_dotenv(root)
    run_server(root, args.host, args.port)


if __name__ == "__main__":
    main()
