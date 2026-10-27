#!/usr/bin/env bash
set -e

echo "============================================="
echo "RoboWitness - Linux/macOS Bootstrap"
echo "============================================="

if ! command -v python3 &> /dev/null; then
    echo "Python 3.11+ is required but not found."
    exit 1
fi

if [ ! -d "backend/.venv" ]; then
    echo "Creating Python virtual environment in backend/.venv..."
    python3 -m venv backend/.venv
fi

echo "Installing backend dependencies..."
source backend/.venv/bin/activate
pip install --upgrade pip
pip install -e "backend/.[dev]"

mkdir -p artifacts/runs artifacts/verifications

if command -v npm &> /dev/null; then
    echo "Installing frontend dependencies..."
    cd apps/web && npm install && cd ../..
fi

echo "Bootstrap complete!"
