#!/bin/bash

# Setup script for Linux/macOS
# This script sets up the Python virtual environment and installs dependencies

echo "===================================="
echo "Setting up secure Flask application"
echo "===================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Set environment variables (for development only)
echo ""
echo "Setting environment variables..."
export PAYMENT_TOKEN="tok_development_token"
export MAIL_SERVER_KEY="mail_srv_key_dev"
export INTERNAL_AUTH="admin_internal_dev_key"
export FLASK_DEBUG="True"

# Create logs directory
echo "Creating logs directory..."
mkdir -p logs

# Create dummy database if it doesn't exist
if [ ! -f appdata.db ]; then
    echo "Creating dummy database..."
    sqlite3 appdata.db "CREATE TABLE profiles (id INTEGER PRIMARY KEY, name TEXT, balance REAL);"
    sqlite3 appdata.db "INSERT INTO profiles (id, name, balance) VALUES (1, 'John Doe', 1000.00);"
    sqlite3 appdata.db "INSERT INTO profiles (id, name, balance) VALUES (2, 'Jane Smith', 2500.50);"
fi

echo ""
echo "===================================="
echo "Setup completed successfully!"
echo "===================================="
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the application, use:"
echo "  python inputs.py"
echo ""
echo "To run tests, use:"
echo "  ./run_test.sh"
echo ""
