#!/bin/bash
# Linux/macOS script to set up virtual environment

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "========================================"
echo "Virtual environment setup complete!"
echo "========================================"
echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "To deactivate, simply type:"
echo "  deactivate"
echo ""
