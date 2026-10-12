import sys
import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from sorts.database.connection import init_db, get_db
from sorts.services.seed_service import seed_database, seed_global_traits
from sorts.database import models as db_models
from sorts.bot.bot import run_bot

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


import json
from urllib.parse import urlparse, parse_qs
from sorts.web.compliance import TERMS_HTML, PRIVACY_HTML
from sorts.web.api import handle_api_request


class _HealthHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            params = parse_qs(parsed.query)
            status, data = handle_api_request(path, "GET", params, {})
            self._send_json(status, data)
            return

        if path == "/terms":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(TERMS_HTML.encode("utf-8"))
        elif path == "/privacy":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(PRIVACY_HTML.encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                body_data = json.loads(body)
            except Exception:
                body_data = {}
            params = parse_qs(parsed.query)
            status, data = handle_api_request(path, "POST", params, body_data)
            self._send_json(status, data)
            return

        self.send_response(404)
        self.end_headers()

    def _send_json(self, status: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # Silence access logs


def start_health_server():
    """Starts a minimal HTTP server on PORT so Render & UptimeRobot health checks pass."""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health server running on port {port}")

def bootstrap():
    """Initializes database schema, seeds global traits, seeds university data, and imports clubs if missing."""
    logger.info("Initializing database schema...")
    init_db()

    with get_db() as db:
        # ── Always seed global traits first (safe for all universities) ──────
        seed_global_traits(db)

        # ── Seed Mahindra University if not already in database ──────────────
        # Data lives in Supabase after the first deploy; seed file only needed
        # on a completely fresh database (e.g. first migration to Supabase).
        mahindra = db.query(db_models.University).filter_by(slug="mahindra").first()
        if not mahindra:
            seed_path = "sorts/assets/data/mahindra_seed.json"
            if os.path.exists(seed_path):
                logger.info("Mahindra University not found in DB. Running auto-seeding from file...")
                try:
                    seed_database(db, seed_path)
                    logger.info("Auto-seeding completed.")
                    mahindra = db.query(db_models.University).filter_by(slug="mahindra").first()
                except Exception as e:
                    logger.error(f"Auto-seeding failed: {e}")
                    return
            else:
                # Seed file has been removed from the repo after the initial
                # Supabase migration — this is expected and fine. Mahindra data
                # already lives in the persistent database.
                logger.info(
                    "Mahindra seed file not present and university not found in DB. "
                    "If this is intentional (data is in Supabase), this is fine. "
                    "Otherwise restore sorts/assets/data/mahindra_seed.json and redeploy."
                )
                return
        else:
            logger.info("Mahindra University records present in database. Skipping seed.")

        # ── Auto-import clubs if none are published yet ──────────────────────
        club_count = db.query(db_models.Club).filter_by(
            university_id=mahindra.id
        ).count()

        if club_count == 0:
            logger.info("No clubs found. Running auto-import from source...")
            try:
                from sorts.services.import_service import ImportService
                svc = ImportService()
                sources = svc.get_university_sources(db, mahindra.id)
                if not sources:
                    logger.warning("No import sources configured for Mahindra University.")
                    return
                # Prefer live website source (type='website') over static test file (type='file')
                live_source = next((s for s in sources if s.source_type == "website"), sources[-1])
                logger.info(f"Selected live source '{live_source.name}' (ID: {live_source.id})")
                job_id = svc.trigger_import(db, live_source.id)
                logger.info(f"Import job {job_id} complete. Publishing clubs...")
                svc.publish_job(db, job_id)
                published = db.query(db_models.Club).filter_by(
                    university_id=mahindra.id
                ).count()
                logger.info(f"Auto-import done. {published} clubs now live.")
            except Exception as e:
                logger.error(f"Auto-import failed: {e}")
        else:
            logger.info(f"{club_count} clubs already live. Skipping auto-import.")

        # ── Ensure Verified Club Registry and Events are synchronized ─────────
        try:
            from sorts.services.seed_service import sync_verified_clubs, sync_verified_events
            sync_verified_clubs(db)
            sync_verified_events(db)
        except Exception as e:
            logger.error(f"Failed to sync verified registry or events: {e}")

def main():
    start_health_server()  # Open port before anything else so Render health check passes
    bootstrap()
    logger.info("Starting Sortling Discord Bot...")
    run_bot()

if __name__ == "__main__":
    main()
