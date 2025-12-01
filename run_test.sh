#!/usr/bin/env bash
set -e

# Run security tests for both backup and patched modules
python -u tests/run_tests.py

if [ $? -eq 0 ]; then
  echo "TEST PASSED"
  exit 0
else
  echo "TEST FAILED"
  exit 1
fi
