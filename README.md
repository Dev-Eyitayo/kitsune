# kitsune

> Shape-shift any website into a standalone, isolated desktop web app across Linux and Windows.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-brightgreen.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%2F%20Windows-orange.svg)]()
[![Browsers](https://img.shields.io/badge/browsers-Firefox%20%7C%20Edge%20%7C%20Brave%20%7C%20Chrome%20%7C%20Zen-blue.svg)]()

---

## Overview

Desktop Firefox does not provide native Progressive Web App (PWA) or Site-Specific Browser (SSB) installation support. Users who prefer Firefox or specific browsers for privacy and open-source principles often struggle with running web apps (such as WhatsApp Web, ChatGPT, Claude, Discord, or Notion) as standalone desktop clients.

**kitsune** is a zero-dependency CLI tool and desktop integration manager that transforms any web application into a first-class desktop app powered by your choice of browser engine (**Firefox, Microsoft Edge, Brave, Google Chrome, Zen Browser, LibreWolf, or Chromium**).

---

## Key Features

* **Complete Profile Sandboxing:** Each application runs in its own dedicated profile with isolated cookies, local storage, sessions, and cache.
* **Multi-Browser Backend:** Choose your preferred engine (`--browser firefox`, `edge`, `brave`, `chrome`, `zen`, `librewolf`).
* **Cross-Platform (Linux & Windows):** Generates native Freedesktop `.desktop` launchers on Linux and native `.lnk` Start Menu shortcuts on Windows.
* **Wayland & GNOME Dock Separation:** On Linux, bypasses the Wayland `app_id` grouping limitation using XWayland window class targeting (`--class`, `--name`, and `StartupWMClass`), ensuring independent dock icons and taskbar grouping.
* **Native Frameless Window:** Automatically injects custom `userChrome.css` for Gecko engines and leverages `--app=` flags for Chromium engines.
* **Intelligent External Link Routing:** Outbound links clicked inside web apps are automatically forwarded to your primary browsing window.
* **Zero External Dependencies:** Built entirely with the Python standard library. Requires no third-party package installations.

---

## Quickstart & Installation

### Linux (Ubuntu, Mint, Debian, Arch, Fedora)

```bash
curl -sSL https://raw.githubusercontent.com/dev-eyitayo/kitsune/main/install.sh | bash
```

### Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/dev-eyitayo/kitsune/main/install.ps1 | iex
```

### Clone and Install Locally

```bash
git clone https://github.com/dev-eyitayo/kitsune.git
cd kitsune
./install.sh   # On Linux
# or .\install.ps1 on Windows
```

---

## Usage Guide

### 1. Interactive Creation Wizard

Launch the wizard without arguments:

```bash
kitsune
```

Follow the interactive prompts to choose an app, browser engine, and shortcut preferences.

### 2. Quick Creation from Built-in Presets

Create popular web applications with pre-configured high-resolution icons and optimal settings:

```bash
# Default Browser (Firefox or system default)
kitsune create whatsapp
kitsune create chatgpt
kitsune create claude
kitsune create discord
kitsune create notion
kitsune create spotify

# Target a Specific Browser Backend
kitsune create whatsapp --browser edge
kitsune create chatgpt --browser brave
kitsune create discord --browser chrome
kitsune create claude --browser zen
```

### 3. Custom Web Application

Create an app from any arbitrary URL:

```bash
kitsune create --name "Grafana Monitoring" --url "https://grafana.internal.net" --icon "https://example.com/grafana.svg" --browser edge
```

#### Optional CLI Flags:
* `-b, --browser`: Choose engine (`firefox`, `edge`, `brave`, `chrome`, `zen`, `librewolf`, `chromium`).
* `--no-pin`: Do not automatically pin the created launcher to the dock/favorites.
* `--no-route`: Keep external links within the web app instead of forwarding to the main browser.
* `--show-ui`: Retain standard browser navigation bars and tabs inside the application window.

### 4. Managing & Updating Applications

```bash
# Detect and list all installed browser backends
kitsune browsers

# Update kitsune from GitHub and refresh all installed web apps automatically
kitsune update

# Refresh configs/styling for all installed web apps
kitsune refresh

# List all installed web applications
kitsune list

# View all available built-in presets
kitsune presets

# Remove an installed web application and delete its profile
kitsune remove whatsapp
```

---

## Supported Environments & Browsers

* **Operating Systems:** Linux (Ubuntu, Linux Mint, Debian, Arch Linux, Fedora, openSUSE) and Windows (10/11).
* **Browsers:** Mozilla Firefox, Microsoft Edge, Brave, Google Chrome, Zen Browser, LibreWolf, Chromium.
* **Linux Display Servers:** Wayland (via XWayland class enforcement) and native X11.
* **Desktop Environments:** GNOME Shell, Cinnamon, KDE Plasma, XFCE, MATE, Windows Start Menu / Taskbar.

---

## Contributing

Contributions are welcome. To add a new application preset, submit a pull request updating `kitsune/presets.py`.

---

## License

MIT License. Copyright (c) 2026 Eyitayo & kitsune Contributors. See [LICENSE](LICENSE) for details.
