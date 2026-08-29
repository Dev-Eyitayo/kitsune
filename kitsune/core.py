"""
Core orchestration logic for kitsune.
Supports multi-browser backends (Firefox, Zen, LibreWolf, Edge, Brave, Chrome) across Linux and Windows.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .browsers import (
    BrowserType,
    SUPPORTED_BROWSERS,
    build_launch_command,
    get_available_browsers,
    get_default_browser,
)
from .desktop import (
    create_desktop_launcher,
    get_applications_dir,
    get_icons_dir,
    is_windows,
    pin_to_gnome_dock,
    save_app_icon,
    unpin_from_gnome_dock,
)
from .link_router import setup_link_router
from .presets import PRESETS
from .profile import create_kitsune_profile, get_firefox_dir, get_profile_dir


def slugify(text: str) -> str:
    """Converts a name into a safe alphanumeric slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def create_app(
    name: str,
    url: str,
    slug: Optional[str] = None,
    browser: Optional[str] = None,
    icon: Optional[str] = None,
    description: str = "",
    categories: str = "Network;WebBrowser;",
    pin_dock: bool = True,
    route_links: bool = True,
    hide_ui: bool = True,
) -> Dict[str, str]:
    """
    Creates a standalone web app with dedicated profile, desktop launcher/shortcut, and dock integration.
    """
    if not slug:
        slug = slugify(name)

    # 1. Resolve target browser
    if browser:
        browser_key = browser.lower()
        conf = SUPPORTED_BROWSERS.get(browser_key, SUPPORTED_BROWSERS["firefox"])
    else:
        browser_key, conf = get_default_browser()

    browser_type = conf["type"]

    # 2. Create isolated profile
    profile_dir = create_kitsune_profile(
        slug=slug,
        url=url,
        browser_type=browser_type,
        hide_browser_ui=hide_ui,
    )

    # 3. Setup link router if requested (Gecko engines)
    if route_links and browser_type == BrowserType.GECKO and not is_windows():
        setup_link_router(profile_dir)

    # 4. Save icon
    icon_path = save_app_icon(slug, icon)

    # 5. Build executable launch command
    launch_cmd = build_launch_command(
        browser_key=browser_key,
        url=url,
        slug=slug,
        profile_dir=profile_dir,
        is_windows=is_windows(),
    )

    # 6. Create desktop launcher / Windows shortcut
    desktop_file = create_desktop_launcher(
        slug=slug,
        name=name,
        url=url,
        launch_command=launch_cmd,
        icon_path=icon_path,
        description=description,
        categories=categories,
    )

    # 7. Pin to dock
    pinned = False
    if pin_dock:
        pinned = pin_to_gnome_dock(desktop_file.name)

    # 8. Write app metadata manifest inside profile dir for portable inspection
    manifest_path = profile_dir / "kitsune.json"
    manifest_data = {
        "name": name,
        "slug": slug,
        "url": url,
        "browser": browser_key,
        "browser_type": browser_type,
        "launcher": str(desktop_file),
        "icon": str(icon_path),
    }
    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
    except Exception:
        pass

    return {
        "slug": slug,
        "name": name,
        "url": url,
        "browser": conf["name"],
        "profile_dir": str(profile_dir),
        "desktop_file": str(desktop_file),
        "icon_path": str(icon_path),
        "pinned": str(pinned),
    }


def list_apps() -> List[Dict[str, str]]:
    """
    Finds and lists all installed Kitsune web applications.
    """
    apps_dir = get_applications_dir()
    results = []

    # Search for Linux .desktop or Windows .lnk
    pattern = "*.lnk" if is_windows() else "kitsune-*.desktop"

    for df in sorted(apps_dir.glob(pattern)):
        slug = df.stem.replace("kitsune-", "").lower()
        name = df.stem.replace("kitsune-", "").capitalize()
        url = "N/A"
        browser_name = "Firefox"

        # Check for kitsune.json manifest
        profile_candidates = [
            get_profile_dir(slug, "gecko"),
            get_profile_dir(slug, "chromium"),
        ]
        for pdir in profile_candidates:
            manifest = pdir / "kitsune.json"
            if manifest.exists():
                try:
                    with open(manifest, "r", encoding="utf-8") as mf:
                        mdata = json.load(mf)
                        name = mdata.get("name", name)
                        url = mdata.get("url", url)
                        browser_name = mdata.get("browser", browser_name).capitalize()
                        profile_candidates = [pdir]
                        break
                except Exception:
                    pass

        # Fallback Linux .desktop parsing
        if url == "N/A" and not is_windows() and df.suffix == ".desktop":
            try:
                with open(df, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("Name=") and not line.startswith("Name=Open"):
                            name = line.split("=", 1)[1].strip()
                        elif line.startswith("Exec="):
                            # extract URL if present at the end
                            parts = line.strip().split()
                            if parts and parts[-1].startswith(('"http', "http")):
                                url = parts[-1].strip('"')
            except Exception:
                pass

        results.append({
            "slug": slug,
            "name": name,
            "url": url,
            "browser": browser_name,
            "profile_dir": str(profile_candidates[0]),
            "desktop_file": str(df),
        })

    return results


def refresh_all_apps() -> List[Dict[str, str]]:
    """
    Refreshes all installed web apps with the latest configuration templates and desktop launchers.
    """
    apps = list_apps()
    refreshed = []
    for app in apps:
        slug = app["slug"]
        url = app["url"]
        name = app["name"]
        browser = app.get("browser", "firefox").lower()
        if url and url != "N/A":
            create_app(
                name=name,
                url=url,
                slug=slug,
                browser=browser,
                pin_dock=False,
                route_links=True,
                hide_ui=True,
            )
            refreshed.append(app)
    return refreshed


def update_kitsune() -> Dict[str, Any]:
    """
    Updates kitsune codebase from GitHub and refreshes all installed web applications.
    """
    repo_url = "https://github.com/dev-eyitayo/kitsune.git"
    install_dir = Path(os.environ.get("APPDATA", Path.home())) / "kitsune" if is_windows() else Path.home() / ".local" / "share" / "kitsune"
    updated_code = False

    # 1. Update the kitsune installation files
    if (install_dir / ".git").exists():
        try:
            subprocess.run(
                ["git", "-C", str(install_dir), "pull", "origin", "main"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            updated_code = True
        except Exception:
            pass
    elif install_dir.exists():
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                subprocess.run(
                    ["git", "clone", "--depth", "1", repo_url, tmp_dir],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                for item in Path(tmp_dir).iterdir():
                    if item.name != ".git":
                        dest = install_dir / item.name
                        if item.is_dir():
                            shutil.copytree(item, dest, dirs_exist_ok=True)
                        else:
                            shutil.copy2(item, dest)
            updated_code = True
        except Exception:
            pass

    # 2. Refresh all installed web apps with latest configs
    refreshed_apps = refresh_all_apps()

    return {
        "updated_code": updated_code,
        "refreshed_apps": refreshed_apps,
    }


def remove_app(slug: str) -> bool:
    """
    Uninstalls a Kitsune web application and cleans up all associated files.
    """
    apps_dir = get_applications_dir()
    icons_dir = get_icons_dir()

    pattern = f"{slug}.lnk" if is_windows() else f"kitsune-{slug}.desktop"
    desktop_file = apps_dir / pattern

    # 1. Unpin from dock (Linux)
    if not is_windows():
        unpin_from_gnome_dock(desktop_file.name)

    # 2. Remove desktop launcher / shortcut
    if desktop_file.exists():
        desktop_file.unlink()

    # 3. Remove icon files
    for icon_file in icons_dir.glob(f"kitsune-{slug}.*"):
        try:
            icon_file.unlink()
        except Exception:
            pass

    # 4. Remove profile directories
    for pdir in [get_profile_dir(slug, "gecko"), get_profile_dir(slug, "chromium")]:
        if pdir.exists():
            try:
                shutil.rmtree(pdir)
            except Exception:
                pass

    return True
