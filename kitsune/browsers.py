"""
Browser detection and engine execution abstraction for kitsune.
Supports Gecko (Firefox, Zen, LibreWolf, Waterfox) and Chromium (Edge, Brave, Chrome, Chromium).
"""
    
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class BrowserType:
    GECKO = "gecko"
    CHROMIUM = "chromium"


# Recognized browser configurations
SUPPORTED_BROWSERS = {
    "firefox": {
        "name": "Mozilla Firefox",
        "type": BrowserType.GECKO,
        "linux_bins": ["firefox", "firefox-esr"],
        "win_bins": [
            "firefox.exe",
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        ],
    },
    "zen": {
        "name": "Zen Browser",
        "type": BrowserType.GECKO,
        "linux_bins": ["zen-browser", "zen"],
        "win_bins": [
            "zen.exe",
            rf"{os.environ.get('LOCALAPPDATA', '')}\Zen Browser\zen.exe",
            r"C:\Program Files\Zen Browser\zen.exe",
        ],
    },
    "librewolf": {
        "name": "LibreWolf",
        "type": BrowserType.GECKO,
        "linux_bins": ["librewolf"],
        "win_bins": [
            "librewolf.exe",
            r"C:\Program Files\LibreWolf\librewolf.exe",
        ],
    },
    "edge": {
        "name": "Microsoft Edge",
        "type": BrowserType.CHROMIUM,
        "linux_bins": ["microsoft-edge-stable", "microsoft-edge", "msedge"],
        "win_bins": [
            "msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
    },
    "brave": {
        "name": "Brave Browser",
        "type": BrowserType.CHROMIUM,
        "linux_bins": ["brave-browser", "brave"],
        "win_bins": [
            "brave.exe",
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            rf"{os.environ.get('LOCALAPPDATA', '')}\BraveSoftware\Brave-Browser\Application\brave.exe",
        ],
    },
    "chrome": {
        "name": "Google Chrome",
        "type": BrowserType.CHROMIUM,
        "linux_bins": ["google-chrome-stable", "google-chrome", "chrome"],
        "win_bins": [
            "chrome.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            rf"{os.environ.get('LOCALAPPDATA', '')}\Google\Chrome\Application\chrome.exe",
        ],
    },
    "chromium": {
        "name": "Chromium",
        "type": BrowserType.CHROMIUM,
        "linux_bins": ["chromium-browser", "chromium"],
        "win_bins": [
            "chromium.exe",
            r"C:\Program Files\Chromium\Application\chromium.exe",
        ],
    },
}


def find_browser_binary(browser_key: str) -> Optional[str]:
    """Finds the executable binary path for a given browser."""
    conf = SUPPORTED_BROWSERS.get(browser_key.lower())
    if not conf:
        return None

    is_windows = sys.platform == "win32"
    candidates = conf["win_bins"] if is_windows else conf["linux_bins"]

    for c in candidates:
        if not c:
            continue
        # Direct file path
        if os.path.isabs(c) and os.path.exists(c):
            return c
        # Path resolution in PATH
        found = shutil.which(c)
        if found:
            return found

    return None


def get_available_browsers() -> Dict[str, Dict[str, str]]:
    """Returns all supported browsers currently detected on this machine."""
    available = {}
    for key, conf in SUPPORTED_BROWSERS.items():
        bin_path = find_browser_binary(key)
        if bin_path:
            available[key] = {
                "name": conf["name"],
                "type": conf["type"],
                "binary": bin_path,
            }
    return available


def get_default_browser() -> Tuple[str, Dict[str, str]]:
    """
    Returns the primary detected browser. Prefers Firefox, then Edge/Chrome/Brave.
    """
    available = get_available_browsers()
    for preferred in ["firefox", "zen", "edge", "brave", "chrome", "librewolf", "chromium"]:
        if preferred in available:
            return preferred, available[preferred]

    # Fallback to firefox entry even if not found in path
    return "firefox", {
        "name": "Mozilla Firefox",
        "type": BrowserType.GECKO,
        "binary": "firefox.exe" if sys.platform == "win32" else "firefox",
    }


def build_launch_command(
    browser_key: str,
    url: str,
    slug: str,
    profile_dir: Path,
    is_windows: bool = False,
) -> str:
    """
    Generates the exact CLI launch command string for the target browser and platform.
    """
    conf = SUPPORTED_BROWSERS.get(browser_key.lower(), SUPPORTED_BROWSERS["firefox"])
    b_type = conf["type"]
    b_bin = find_browser_binary(browser_key) or (conf["win_bins"][0] if is_windows else conf["linux_bins"][0])

    wm_class = f"kitsune-{slug}"

    if is_windows:
        if b_type == BrowserType.CHROMIUM:
            return f'"{b_bin}" --app="{url}" --user-data-dir="{profile_dir}"'
        else:
            return f'"{b_bin}" -profile "{profile_dir}" "{url}"'
    else:
        # Linux
        if b_type == BrowserType.CHROMIUM:
            return f'"{b_bin}" --app="{url}" --user-data-dir="{profile_dir}" --class="{wm_class}"'
        else:
            # Firefox / Gecko with XWayland separation
            return f'env GDK_BACKEND=x11 "{b_bin}" --class {wm_class} --name {wm_class} --new-instance --profile "{profile_dir}" "{url}"'
