# kitsune

> Shape-shift any website into a standalone, isolated desktop web app using Firefox on Linux.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-brightgreen.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%2F%20Ubuntu%20%2F%20Debian%20%2F%20Arch%20%2F%20Fedora-orange.svg)]()
[![Firefox Compatible](https://img.shields.io/badge/Firefox-120%2B-ff7139.svg)](https://www.mozilla.org/firefox/)

---

## Overview

Desktop Firefox does not provide native Progressive Web App (PWA) or Site-Specific Browser (SSB) installation support. Users who prefer Firefox for privacy and open-source principles over Chromium-based alternatives often struggle with running web apps (such as WhatsApp Web, ChatGPT, Claude, Discord, or Notion) as standalone desktop clients.

**kitsune** is a zero-dependency CLI tool and desktop integration manager that transforms any web application into a first-class Linux desktop app powered by Firefox.

---

## Key Features

* **Complete Profile Sandboxing:** Each application runs in its own dedicated Firefox profile with isolated cookies, local storage, sessions, and cache.
* **Wayland & GNOME Dock Separation:** Bypasses the Wayland `app_id` grouping limitation using XWayland window class targeting (`--class`, `--name`, and `StartupWMClass`), ensuring independent dock icons and taskbar grouping.
* **Native Frameless Window:** Automatically injects custom `userChrome.css` to remove tabs, URL address bars, and navigation toolbars while retaining native Linux window controls.
* **Intelligent External Link Routing:** Outbound links clicked inside the web app (e.g., articles, repositories, external portals) are automatically forwarded to your primary daily Firefox browser window via a native messaging bridge.
* **Zero External Dependencies:** Built entirely with the Python standard library (`sqlite3`, `configparser`, `urllib`, `subprocess`, `json`). Requires no third-party package installations.
* **Clean System Integration:** Auto-generates standard Freedesktop `.desktop` files, fetches high-resolution application icons, and integrates directly with GNOME Shell favorites (`favorite-apps`).

---

## Comparison Matrix

| Feature | kitsune (Firefox) | Native Firefox Desktop | Chromium / Chrome PWA | Electron Apps |
| :--- | :--- | :--- | :--- | :--- |
| **Engine** | Gecko (Firefox) | Gecko (Firefox) | Blink (Chromium) | Bundled Chromium |
| **PWA / Standalone Window** | Yes | No (Removed in FF 85) | Yes | Yes |
| **Isolated Cookies & Storage** | Yes (Per-App Profile) | Shared | Shared / Profiles | Isolated |
| **Independent Dock Icon** | Yes (Native Docking) | Merged under Firefox | Yes | Yes |
| **External Link Delegation** | Yes (Routes to Main FF) | N/A | Manual | Inconsistent |
| **Memory Footprint** | Shared Gecko Binaries | Baseline | Chromium Process | Heavy (Per-app Node) |
| **Telemetry / Tracking** | Privacy-respecting | Standard | Google Tracking | Vendor-dependent |

---

## Quickstart & Installation

### Option 1: Automated One-Line Install

```bash
curl -sSL https://raw.githubusercontent.com/dev-eyitayo/kitsune/main/install.sh | bash
```

### Option 2: Clone and Install Locally

```bash
git clone https://github.com/dev-eyitayo/kitsune.git
cd kitsune
./install.sh
```

---

## Usage Guide

### 1. Interactive Creation Wizard

Launch the wizard without arguments:

```bash
kitsune
```

Follow the prompts to enter an application name, URL, icon, and preferences.

### 2. Quick Creation from Built-in Presets

Create popular web applications with pre-configured icons, categories, and optimal window settings:

```bash
# Messaging & Communication
kitsune create whatsapp
kitsune create discord
kitsune create slack
kitsune create messages

# AI & Productivity
kitsune create chatgpt
kitsune create claude
kitsune create notion
kitsune create github

# Media & Entertainment
kitsune create spotify
kitsune create youtube-music
kitsune create x
```

### 3. Custom Web Application

Create an app from any arbitrary URL with custom metadata:

```bash
kitsune create --name "Grafana Monitoring" --url "https://grafana.internal.net" --icon "https://example.com/grafana.svg"
```

#### Optional CLI Flags:
* `--no-pin`: Do not automatically pin the created launcher to the Ubuntu / GNOME dock.
* `--no-route`: Keep external links within the web app instead of forwarding to the main browser.
* `--show-ui`: Retain standard Firefox navigation bars and tabs inside the application window.

### 4. Managing Applications

```bash
# List all installed web applications
kitsune list

# View all available built-in presets
kitsune presets

# Remove an installed web application and delete its profile
kitsune remove whatsapp
```

---

## Architecture & System Flow

```
[ kitsune CLI ]
       |
       +---> [ Profile Sandbox ] ---------> ~/.mozilla/firefox/kitsune-<slug>/
       |     - user.js (suppress tours, sync, duplicates)
       |     - chrome/userChrome.css (hide nav-bar, tab-bar)
       |
       +---> [ Desktop Launcher ] -------> ~/.local/share/applications/kitsune-<slug>.desktop
       |     - StartupWMClass=kitsune-<slug>
       |     - GDK_BACKEND=x11
       |
       +---> [ Icon Manager ] -----------> ~/.local/share/icons/kitsune-<slug>.(svg|png)
       |
       +---> [ Native Link Router ] -----> ~/.local/share/kitsune/router.py
             - WebExtension interceptor
             - Routes external links to primary Firefox profile
```

1. **Profile Generation:** Creates an isolated profile under `~/.mozilla/firefox/kitsune-<slug>` and writes optimized `user.js` configurations to silence first-run screens and disable session restore duplication.
2. **UI Styling:** Deploys `userChrome.css` rules that collapse `#TabsToolbar` and `#nav-bar` while retaining OS window controls.
3. **Window Identity:** Invokes Firefox with `env GDK_BACKEND=x11 firefox --class kitsune-<slug> --name kitsune-<slug>` to guarantee GNOME Shell maps the window to `StartupWMClass=kitsune-<slug>`.
4. **Link Routing Bridge:** Deploys a Native Messaging host manifest (`pwalinks.json`) and a Python bridge that intercepts outbound `<a>` navigation and dispatches it directly to `firefox --profile <main_profile> --new-tab <url>`.

---

## Supported Environments

* **Operating Systems:** Ubuntu (20.04, 22.04, 24.04+), Debian, Arch Linux, Fedora, Pop!_OS, Linux Mint, openSUSE.
* **Display Servers:** Wayland (via XWayland class enforcement) and native X11.
* **Desktop Environments:** GNOME Shell, KDE Plasma, XFCE, Cinnamon, MATE.
* **Firefox Distributions:** Native APT (.deb), Mozilla Tarball, Snap, and Flatpak.

---

## Frequently Asked Questions (FAQ)

#### Does this use more RAM than regular Firefox?
No. Firefox shares its underlying binary and rendering libraries across instances. Profile sandboxing introduces negligible memory overhead while isolating site storage and cookies.

#### Why does it use XWayland instead of pure Wayland?
In native Wayland mode, Firefox hardcodes its Wayland `app_id` to `"firefox"`, causing the GNOME dock to group all windows under the default Firefox launcher. Running the web app launcher through XWayland allows exact `WM_CLASS` assignment, ensuring independent dock icons with separate running indicators.

#### What happens if my main Firefox browser is closed when I click a link?
`kitsune`'s link router explicitly targets your primary browsing profile. If Firefox is closed, Linux launches a fresh instance of your primary browser profile and opens the link as a new tab, leaving your web app window untouched.

---

## Contributing

Contributions are welcome. To add a new application preset, submit a pull request updating `kitsune/presets.py`.

---

## License

MIT License. Copyright (c) 2026 Eyitayo & kitsune Contributors. See [LICENSE](LICENSE) for details.
