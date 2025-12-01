#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TARGET_FILE="${TARGET_FILE:-input.py}"
cd "$ROOT_DIR"
python -m unittest tests.test_security
