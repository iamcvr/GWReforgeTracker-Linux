#!/bin/bash
# install.sh
# Automates the setup process inside the specific Distrobox container.
# This script:
# 1. Creates the Python virtual environment
# 2. Installs Python dependencies
# 3. Exports the CLI command and Desktop Shortcut to the host system

set -e

# Ensure we are in the script directory
cd "$(dirname "$0")"

echo "=== GW Reforge Tracker Installer ==="

# Check for system dependencies (basic check)
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed. Please install python3, python3-pip, python3-venv, and python3-tk."
    exit 1
fi

# 1. Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[+] Creating Python virtual environment..."
    python3 -m venv .venv
else
    echo "[!] .venv already exists, skipping creation."
fi

# 2. Install Dependencies
echo "[+] Installing/Updating Python dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install requests beautifulsoup4 customtkinter

# 3. Permissions
echo "[+] Making run_linux.sh executable..."
chmod +x run_linux.sh

# 4. Exports
if command -v distrobox-export &> /dev/null; then
    echo "[+] Exporting 'gwtracker' command to host..."
    # --yes to avoid prompts if overwriting
    distrobox-export --bin "$(pwd)/run_linux.sh" --export-label gwtracker --yes

    echo "[+] Exporting Desktop Shortcut..."
    # Prepare the desktop file from template
    cp gwtracker.desktop.template gwtracker.desktop
    
    # Export
    distrobox-export --app ./gwtracker.desktop --yes
else
    echo "[-] 'distrobox-export' not found. Are you running this inside a Distrobox?"
    echo "    Skipping host export steps."
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "1. Run 'gwtracker' from your terminal."
echo "2. Find 'GW Reforge Tracker' in your App Menu."
echo "=========================================="
