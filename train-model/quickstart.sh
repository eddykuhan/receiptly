#!/bin/bash

# Quick start script for Receipt NER Model

echo "=========================================="
echo "Receipt Merchant & Location Extraction"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Train model
echo ""
echo "Training model..."
python train_model.py

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "To use the model:"
echo "  1. Interactive mode: python predict.py"
echo "  2. See examples: python integration_examples.py"
echo "  3. Add more data: Edit sample_data.csv and re-run train_model.py"
echo ""
echo "Documentation:"
echo "  - README.md - Project overview"
echo "  - HOW_TO_IMPROVE.md - Guide to improve accuracy"
echo ""
