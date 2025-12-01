#!/usr/bin/env bash
set -e
python -m venv venv
. venv/bin/activate
pip install -r requirements.txt
echo "Environment set up. Activate with: source venv/bin/activate" 
