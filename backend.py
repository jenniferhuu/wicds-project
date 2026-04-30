from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from skincare_engine import SkincareRecommender, UserProfile, options_payload


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
RECOMMENDER = SkincareRecommender.from_files(
    ROOT / "products_processed.json",
    ROOT / "ingredients_kb.json",
)


class SkincareRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json(
                {
                    "status": "ok",
                    "products": len(RECOMMENDER.products),
                    "ingredients": len(RECOMMENDER.ingredients),
                }
            )
            return
        if path == "/api/options":
            self._send_json(options_payload())
            return
        if path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/recommend":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            profile = UserProfile(
                skin_type=payload.get("skin_type", "normal"),
                concerns=payload.get("concerns", []),
                allergies=payload.get("allergies", []),
                age_range=payload.get("age_range", "30s"),
                climate=payload.get("climate", "temperate"),
                budget=payload.get("budget", "any"),
                pregnancy=bool(payload.get("pregnancy", False)),
                sensitivity_level=payload.get("sensitivity_level", "normal"),
            )
            self._send_json(RECOMMENDER.recommend(profile))
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json({"error": "Request body must be valid JSON"}, HTTPStatus.BAD_REQUEST)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), SkincareRequestHandler)
    print(f"SkinSync demo running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
    )
