#!/bin/bash
# run_linux.sh
# Wrapper to run the tracker inside the Distrobox container
# correctly using the virtual environment.

cd "$(dirname "$0")" || exit
source .venv/bin/activate
python3 linux_tracker.py "$@"
