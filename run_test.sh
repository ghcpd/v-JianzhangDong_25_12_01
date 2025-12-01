#!/usr/bin/env bash
# Run tests for specified module (backup or fixed) via MODULE_UNDER_TEST
set -e
MODULE=${1:-backup}
export MODULE_UNDER_TEST=${MODULE}
python -m pytest -q tests/test_input.py
