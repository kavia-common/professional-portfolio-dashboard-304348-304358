#!/bin/bash
set -euo pipefail

cd /home/kavia/workspace/code-generation/professional-portfolio-dashboard-304348-304358/portfolio_backend

# CI environments may not have a venv pre-created. Create it if missing.
if [ ! -f "venv/bin/activate" ]; then
  python -m venv venv
fi

source venv/bin/activate

# Ensure lint dependency is available in the active environment.
python -m pip install -q -r requirements.txt

# Run flake8 via module to avoid PATH issues.
python -m flake8 .

