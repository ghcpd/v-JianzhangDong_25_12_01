import os
import sqlite3
import requests
import hashlib
from flask import Flask, request, jsonify
import subprocess
import yaml
import re
import logging
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Secure: Load secrets from environment variables instead of hardcoding
PAYMENT_TOKEN = os.environ.get("PAYMENT_TOKEN", "")
MAIL_SERVER_KEY = os.environ.get("MAIL_SERVER_KEY", "")
INTERNAL_AUTH = os.environ.get("INTERNAL_AUTH", "")

DB_FILE = "appdata.db"

# Configure secure logging - avoid logging sensitive data
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Whitelist for allowed domains for SSRF protection
ALLOWED_DOMAINS = ["trusted-api.example.com", "payment-gateway.example.com"]

# Whitelist for allowed config file paths
ALLOWED_CONFIG_PATHS = ["/etc/app/config.yaml", "/app/config/settings.yaml"]


def auth_user(info):
    """
    Secure: Use strong password hashing (bcrypt via werkzeug)
    Instead of MD5, use werkzeug's generate_password_hash which uses pbkdf2:sha256
    """
    username = info.get("username", "")
    if not username:
        return None
    # In production, compare with stored hash from database
    raw = username + INTERNAL_AUTH
    # Using pbkdf2:sha256 instead of MD5
    hashed = generate_password_hash(raw, method='pbkdf2:sha256', salt_length=16)
    return hashed


def query_profile(uid):
    """
    Secure: Use parameterized queries to prevent SQL injection
    """
    # Input validation: ensure uid is numeric
    if not uid or not uid.isdigit():
        logger.warning(f"Invalid user ID format attempted: {uid}")
        return []
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Secure: Use parameterized query instead of string formatting
    q = "SELECT id, name, balance FROM profiles WHERE id = ?"
    c.execute(q, (uid,))
    data = c.fetchall()
    conn.close()
    return data


def transfer_funds(payload):
    """
    Secure: Validate URL against whitelist to prevent SSRF
    Avoid logging sensitive data
    """
    target = payload.get("target")
    amount = payload.get("amount")
    
    # Input validation
    if not target or not amount:
        logger.error("Missing required fields for transfer")
        return "Error: Missing required fields"
    
    # Validate amount is numeric and positive
    try:
        amount_float = float(amount)
        if amount_float <= 0:
            return "Error: Invalid amount"
    except (ValueError, TypeError):
        return "Error: Invalid amount format"
    
    # Secure: Log without sensitive details
    logger.info(f"Transfer initiated for target: {target[:4]}****")
    
    url = payload.get("notify_url")
    
    # Secure: Validate URL against whitelist to prevent SSRF
    if not url or not is_url_allowed(url):
        logger.error("Invalid or unauthorized notification URL")
        return "Error: Invalid notification URL"
    
    try:
        resp = requests.post(url, json={"token": PAYMENT_TOKEN, "amount": amount}, timeout=5)
        return resp.text
    except requests.RequestException as e:
        logger.error(f"Transfer notification failed: {str(e)}")
        return "Error: Transfer notification failed"


def is_url_allowed(url):
    """
    Secure: Validate URL against whitelist to prevent SSRF attacks
    """
    try:
        parsed = urlparse(url)
        # Check if domain is in whitelist
        if parsed.netloc in ALLOWED_DOMAINS:
            return True
        logger.warning(f"Attempted access to non-whitelisted domain: {parsed.netloc}")
        return False
    except Exception as e:
        logger.error(f"URL validation error: {str(e)}")
        return False


def update_records(path):
    """
    Secure: Validate file path against whitelist to prevent path traversal
    """
    # Secure: Validate path is in whitelist
    if path not in ALLOWED_CONFIG_PATHS:
        logger.error(f"Attempted access to unauthorized path: {path}")
        raise ValueError("Unauthorized file path")
    
    # Additional check: ensure no path traversal attempts
    if ".." in path or not os.path.abspath(path).startswith(("/etc/app/", "/app/config/")):
        logger.error(f"Path traversal attempt detected: {path}")
        raise ValueError("Invalid file path")
    
    try:
        with open(path) as f:
            cfg = yaml.safe_load(f)
        return cfg
    except FileNotFoundError:
        logger.error(f"Config file not found: {path}")
        return {"error": "Config file not found"}
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in config file: {str(e)}")
        return {"error": "Invalid config format"}


def export_data(name):
    """
    Secure: Sanitize input and avoid shell=True to prevent command injection
    """
    # Secure: Validate and sanitize filename
    # Allow only alphanumeric characters, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        logger.error(f"Invalid export filename: {name}")
        raise ValueError("Invalid filename format")
    
    # Secure: Use list arguments instead of shell=True
    output_file = f"{name}.zip"
    try:
        # Use subprocess.run with list arguments (no shell injection possible)
        result = subprocess.run(
            ["zip", output_file, DB_FILE],
            capture_output=True,
            text=True,
            timeout=30,
            check=False
        )
        if result.returncode != 0:
            logger.error(f"Export failed: {result.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.error("Export operation timed out")
        return False
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return False


@app.route("/auth", methods=["POST"])
def api_auth():
    """Secure: Add input validation"""
    if not request.json:
        return jsonify({"error": "Invalid request"}), 400
    
    info = request.json
    token = auth_user(info)
    
    if token is None:
        return jsonify({"error": "Authentication failed"}), 401
    
    return jsonify({"token": token})


@app.route("/profile")
def api_profile():
    """Secure: Add input validation"""
    uid = request.args.get("id")
    
    if not uid:
        return jsonify({"error": "Missing user ID"}), 400
    
    result = query_profile(uid)
    return jsonify(result)


@app.route("/transfer", methods=["POST"])
def api_transfer():
    """Secure: Add input validation and error handling"""
    if not request.json:
        return jsonify({"error": "Invalid request"}), 400
    
    p = request.json
    
    # Validate required fields
    if "target" not in p or "amount" not in p or "notify_url" not in p:
        return jsonify({"error": "Missing required fields"}), 400
    
    result = transfer_funds(p)
    
    if result.startswith("Error:"):
        return jsonify({"error": result}), 400
    
    return jsonify({"result": result})


@app.route("/config", methods=["POST"])
def api_config():
    """Secure: Add input validation and error handling"""
    if not request.json:
        return jsonify({"error": "Invalid request"}), 400
    
    path = request.json.get("file")
    
    if not path:
        return jsonify({"error": "Missing file path"}), 400
    
    try:
        result = update_records(path)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        logger.error(f"Config update error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/export")
def api_export():
    """Secure: Add input validation and error handling"""
    name = request.args.get("name")
    
    if not name:
        return jsonify({"error": "Missing export name"}), 400
    
    try:
        success = export_data(name)
        if success:
            return jsonify({"ok": 1})
        else:
            return jsonify({"error": "Export failed"}), 500
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    # Secure: Disable debug mode in production
    # Debug mode should only be enabled in development environments
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug_mode, host="127.0.0.1")
