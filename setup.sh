#!/bin/bash

# Setup script for Linux/macOS
# This script sets up the environment for running the security audit tests

set -e

echo "=========================================="
echo "Security Audit Setup Script"
echo "=========================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "Found Python: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing required packages..."
pip install -r requirements.txt

# Create config directory
mkdir -p configs

# Create logs directory
mkdir -p logs

echo "=========================================="
echo "Setup completed successfully!"
echo "=========================================="
echo ""
echo "To run tests, execute: ./run_test.sh"
echo "To run auto tests, execute: python3 auto_test.py"
