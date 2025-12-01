#!/bin/bash

# Setup script for Linux/macOS environments
set -e

echo "Setting up Python environment..."

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Create required directories
mkdir -p config logs

# Create a sample config file
if [ ! -f "config/sample.yaml" ]; then
    cat > config/sample.yaml << 'EOF'
# Sample configuration file
database:
  host: localhost
  port: 5432
  name: appdata
logging:
  level: INFO
EOF
fi

echo "Setup complete! Virtual environment created at ./venv"
echo "To activate the environment, run: source venv/bin/activate"
echo "To run the application: python inputs.py"
