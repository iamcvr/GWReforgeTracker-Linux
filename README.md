# Guild Wars Reforge Quest Tracker — Linux Edition

A Linux-native fork of the Guild Wars Reforge Quest Tracker, rewritten to remove the Windows-only PySide6/Qt dependencies and run cleanly across all Linux distributions.

This version uses a lightweight Tkinter UI, a pure-Python wiki scraper, and runs seamlessly inside a Distrobox container so it never pollutes your host system.

## Features
### ✔ Multi-profile support
Track separate quest progress for multiple characters.

### ✔ Quest status tracking
Mark quests as:
- `[ ]` Not Started
- `[~]` In Progress
- `[✔]` Completed

### ✔ Campaign navigation
Supports all major Guild Wars campaigns:
- Prophecies
- Factions
- Nightfall
- Eye of the North
- Pre-Searing
- LDoA path

### ✔ Side-quest grouping
Side quests are automatically grouped under section headers.

### ✔ Collapsible Sections with Icons
- ▾ expanded
- ▸ collapsed

### ✔ Smart search
When searching, only sections that contain matching quests appear — keeping the UI clean and relevant.

### ✔ Pure-Python Guild Wars Wiki sync
A rewritten scraper:
- Downloads updated quest information from the wiki
- Extracts mission + side-quest lists
- Groups quests by region
- Caches pages to reduce wiki load
- Avoids all Qt/QThread dependencies
- Works anywhere Python runs

### ✔ Import / Export
Profiles can be backed up or restored using simple JSON files.

### ✔ Quest completion history
View timestamps of all quests you've completed.

### ✔ “Open in Wiki”
Opens selected quests directly in your browser.

### Why a Linux Edition?
The original project relies heavily on PySide6 + QtWebEngine, which causes several issues on Linux:
- QtWebEngine wheels often missing for certain Python versions
- PySide6 crashes or segfaults under Wine/Proton
- DLL load errors when running the Windows EXE
- Native Linux PySide6 packages incompatible with upstream code

To fix this, the Linux fork:
- Replaces Qt entirely
- Replaces the threaded scraper with a pure Python version
- Uses Tkinter (built-in GUI toolkit)
- Runs in a clean Python environment via Distrobox

# Installation Guide

This installation method does not modify your host system.
Everything is contained inside a Distrobox environment.

### 1. Install Distrobox
```
curl -s https://raw.githubusercontent.com/89luca89/distrobox/main/install | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 2.Create and enter the container
```
distrobox-create -n gwtracker-box -i docker.io/library/ubuntu:24.04
distrobox-enter gwtracker-box
```

### 3. Install Python + Tkinter inside the container
```
sudo apt update
sudo apt install -y python3 python3-tk python3-pip python3-venv
```

### 4. Clone the repo
Inside the container:
```
git clone https://github.com/YOUR_USERNAME/GWReforgeTracker-Linux.git
cd GWReforgeTracker-Linux
```

### 5. Create a Python virtual environment
```
python3 -m venv .venv
source .venv/bin/activate
```

Install required Python packages:
```
pip install requests beautifulsoup4 customtkinter
```

### 6. Installation & Integration (Automated)

**Tested on Fedora/Bazzite/Bluefin (Distrobox)**

Run the included installer to set up the Python environment and export the shortcuts automatically:

```bash
chmod +x install.sh
./install.sh
```

**That's it!**
- Run `gwtracker` from any terminal.
- Launch **GW Reforge Tracker** from your app menu.

---

### Manual Installation (If script fails)
If you prefer to do it manually:

1. **Setup Python:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install requests beautifulsoup4 customtkinter
    ```
2. **Export Command:**
    ```bash
    chmod +x run_linux.sh
    distrobox-export --bin $(pwd)/run_linux.sh --export-label gwtracker
    ```
3. **Export Shortcut:**
    ```bash
    cp gwtracker.desktop.template gwtracker.desktop
    distrobox-export --app ./gwtracker.desktop
    ```

# Troubleshooting
### ❌ “No module named tkinter”
You forgot to install `python3-tk` inside the distrobox.

### ❌ Sync pulls too many random wiki entries
This fork uses an improved scraper that filters out non-quest entries.
If you still get noise, report the campaign and I'll refine the filter.

### ❌ Tracker doesn't appear in app menu
Run:
`update-desktop-database ~/.local/share/applications`
Or log out and back in.

### Credits

Original Windows application:
https://github.com/Mr-Akito/GWReforgeTracker

Linux rewrite & scraper refactor:
[@iamcvr](https://github.com/iamcvr/)

This is a fan-made, open-source utility.

Guild Wars and related assets belong to ArenaNet & NCSoft.