#!/usr/bin/env bash
set -e

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}Installing kitsune (Firefox Web App Manager for Linux)...${NC}"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not installed." >&2
    exit 1
fi

INSTALL_DIR="$HOME/.local/share/kitsune"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$INSTALL_DIR" "$BIN_DIR"

# If running from cloned repo or standalone
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/bin/kitsune" ]; then
    echo "Installing from local repository..."
    cp -r "$SCRIPT_DIR/"* "$INSTALL_DIR/"
else
    echo "Downloading latest kitsune repository..."
    TEMP_DIR=$(mktemp -d)
    git clone --depth 1 https://github.com/dev-eyitayo/kitsune.git "$TEMP_DIR" 2>/dev/null || {
        echo "Git clone failed. Please clone the repository manually." >&2
        exit 1
    }
    cp -r "$TEMP_DIR/"* "$INSTALL_DIR/"
    rm -rf "$TEMP_DIR"
fi

chmod +x "$INSTALL_DIR/bin/kitsune"
ln -sf "$INSTALL_DIR/bin/kitsune" "$BIN_DIR/kitsune"

# Ensure ~/.local/bin is in PATH in .bashrc if not already present
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo -e "${GREEN}Added ~/.local/bin to PATH in ~/.bashrc${NC}"
fi

echo -e "\n${GREEN}${BOLD}[OK] kitsune successfully installed!${NC}"
echo -e "Try running: ${BOLD}kitsune create whatsapp${NC} or ${BOLD}kitsune${NC} for interactive wizard.\n"
