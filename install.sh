#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "============================================================"
echo "  Polymarket BTC 5-Min Bot - Install"
echo "============================================================"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is not installed."
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git is not installed."
  exit 1
fi

echo "[1/4] Creating virtual environment..."
python3 -m venv venv

echo "[2/4] Activating virtual environment..."
# shellcheck disable=SC1091
source venv/bin/activate

echo "[3/4] Installing packages (this may take several minutes)..."
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "[4/4] Creating .env from template..."
if [ ! -f .env ]; then
  cp .env.example .env
fi

echo
echo "  Install complete!  Next: ./start.sh"
echo
