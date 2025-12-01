import os
import sqlite3
import requests
import hmac
import hashlib
import logging
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import yaml
from flask import Flask, request, jsonify

# Logging setup
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Configuration
DB_FILE = os.environ.get("DB_FILE", "appdata.db")
CONFIG_DIR = Path(os.environ.get("CONFIG_DIR", "config")).resolve()
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_NOTIFY_HOSTS = {
    host.strip() for host in os.environ.get("ALLOWED_NOTIFY_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()
}


def get_secret(name: str, default=None, required: bool = False):
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(f"Missing required secret: {name}")
    return val


# Secrets (provide safe defaults for development/testing, require override in production)
PAYMENT_TOKEN = get_secret("PAYMENT_TOKEN", default="dev-payment-token")
MAIL_SERVER_KEY = get_secret("MAIL_SERVER_KEY", default="")
INTERNAL_AUTH_SECRET = get_secret("INTERNAL_AUTH_SECRET", default="dev-internal-secret")


app = Flask(__name__)


# Helpers
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def auth_user(info):
    """Authenticate user by generating an HMAC-based token over the username."""
    username = (info or {}).get("username", "")
    if not username:
        raise ValueError("username required")
    digest = hmac.new(INTERNAL_AUTH_SECRET.encode(), username.encode(), hashlib.sha256).hexdigest()
    return digest


def query_profile(uid):
    """Fetch profile safely using parameterized queries."""
    try:
        uid_int = int(uid)
    except (TypeError, ValueError):
        raise ValueError("invalid user id")

    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, name, balance FROM profiles WHERE id = ?", (uid_int,))
        rows = cur.fetchall()
        return [dict(row) for row in rows]


def _validate_notify_url(url: str) -> str:
    if not url:
        raise ValueError("notify_url required")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("unsupported URL scheme")
    if parsed.hostname not in ALLOWED_NOTIFY_HOSTS:
        raise ValueError("destination host not allowed")
    return parsed.geturl()


def transfer_funds(payload):
    """Transfer funds and notify allowed endpoint securely."""
    payload = payload or {}
    target = payload.get("target")
    amount = payload.get("amount")
    safe_url = _validate_notify_url(payload.get("notify_url"))

    logger.info("transfer target=%s amount=%s notify_host=%s", target, amount, urlparse(safe_url).hostname)
    try:
        resp = requests.post(safe_url, json={"token": PAYMENT_TOKEN, "amount": amount}, timeout=5)
        resp.raise_for_status()
        if resp.headers.get("Content-Type", "").startswith("application/json"):
            return resp.json()
        return resp.text
    except requests.RequestException as exc:
        logger.error("notify failed: %s", exc)
        raise


def update_records(path):
    """Load YAML config from a whitelisted directory, preventing path traversal."""
    if not path:
        raise ValueError("file path required")
    candidate = Path(path)
    resolved = (CONFIG_DIR / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()

    # Ensure resolved path stays within CONFIG_DIR
    if CONFIG_DIR not in resolved.parents and resolved != CONFIG_DIR:
        raise ValueError("invalid config path")

    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError("config file not found")

    with resolved.open() as f:
        cfg = yaml.safe_load(f)
    return cfg


def export_data(name):
    """Safely create a zip archive of the database without shell execution."""
    if not name or not SAFE_NAME_RE.fullmatch(name):
        raise ValueError("invalid export name")

    db_path = Path(DB_FILE)
    if not db_path.exists():
        raise FileNotFoundError("database file not found")

    zip_path = Path(f"{name}.zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(db_path, arcname=db_path.name)
    return True


# Flask routes with basic error handling
@app.errorhandler(Exception)
def handle_error(e):
    status = 400 if isinstance(e, (ValueError, FileNotFoundError)) else 500
    logger.exception("error: %s", e)
    return jsonify({"error": str(e)}), status


@app.route("/auth", methods=["POST"])
def api_auth():
    info = request.json
    return jsonify({"token": auth_user(info)})


@app.route("/profile")
def api_profile():
    uid = request.args.get("id")
    return jsonify(query_profile(uid))


@app.route("/transfer", methods=["POST"])
def api_transfer():
    p = request.json
    return jsonify({"result": transfer_funds(p)})


@app.route("/config", methods=["POST"])
def api_config():
    path = request.json.get("file")
    return jsonify(update_records(path))


@app.route("/export")
def api_export():
    name = request.args.get("name")
    export_data(name)
    return jsonify({"ok": 1})


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    app.run(debug=debug_mode, host=host, port=port)
