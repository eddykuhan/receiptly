#!/bin/bash

# Quick Start Script for Receipt Extractor
# This script helps you set up and test the receipt extractor

echo "=========================================="
echo "Receipt Extractor - Quick Start"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "=========================================="
    echo "⚠️  IMPORTANT: Set your OpenAI API key"
    echo "=========================================="
    echo "Please edit the .env file and add your OpenAI API key:"
    echo "  OPENAI_API_KEY=sk-your-api-key-here"
    echo ""
    echo "You can get your API key from: https://platform.openai.com/api-keys"
    echo ""
else
    echo "✓ .env file found"
    echo ""
fi

# Check for receipts directory
if [ ! -d "receipts" ]; then
    mkdir receipts
    echo "✓ Created receipts/ directory"
else
    echo "✓ receipts/ directory exists"
fi

# Check for output directory
if [ ! -d "output" ]; then
    mkdir output
    echo "✓ Created output/ directory"
else
    echo "✓ output/ directory exists"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Add your OpenAI API key to .env file"
echo "  2. Add receipt images to receipts/ directory"
echo "  3. Run: python receipt_extractor.py receipts/your_receipt.jpg"
echo ""
echo "For batch processing:"
echo "  python batch_processor.py receipts/"
echo ""
echo "For examples:"
echo "  python example_usage.py"
echo ""
echo "=========================================="
