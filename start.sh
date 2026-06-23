#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f venv/bin/activate ]; then
  echo "Run ./install.sh first."
  exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo "Opening dashboard in your browser..."
echo "Keep this terminal open while the bot is running."
echo

exec python -m streamlit run easy_app/main.py --server.headless true
