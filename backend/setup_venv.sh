#!/bin/bash

# FortuneDiary Backend - Python 3.12 Virtual Environment Setup

echo "🐍 Creating Python 3.12 virtual environment..."
python3.12 -m venv .venv

echo "✅ Virtual environment created!"
echo ""
echo "To activate it, run:"
echo "  source .venv/bin/activate"
echo ""
echo "Then install dependencies with:"
echo "  pip install --upgrade pip"
echo "  pip install -e ."
echo ""
echo "Or run this script with the --install flag:"
echo "  bash setup_venv.sh --install"

# If --install flag is provided, activate and install
if [[ "$1" == "--install" ]]; then
    echo ""
    echo "📦 Installing dependencies..."
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -e .
    echo ""
    echo "✅ All done! Virtual environment is ready."
    echo "Activate it with: source .venv/bin/activate"
fi
