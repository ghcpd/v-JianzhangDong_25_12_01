#!/usr/bin/env bash
set -e
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Prepare environment for tests
python -c "import os; os.environ['DB_FILE']='test_appdata.db'"

echo "Setup complete"
