"""
Core orchestration logic for kitsune.
"""

import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from .desktop import (
    create_desktop_launcher,
    get_applications_dir,
    get_icons_dir,
    pin_to_gnome_dock,
    save_app_icon,
    unpin_from_gnome_dock,
)
from .link_router import setup_link_router
from .presets import PRESETS
from .profile import create_kitsune_profile, get_firefox_dir


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
    icon: Optional[str] = None,
    description: str = "",
    categories: str = "Network;WebBrowser;",
    pin_dock: bool = True,
    route_links: bool = True,
    hide_ui: bool = True,
) -> Dict[str, str]:
    """
    Creates a full standalone web app with dedicated profile, desktop launcher, and dock integration.
    """
    if not slug:
        slug = slugify(name)

    # 1. Create dedicated Firefox profile
    profile_dir = create_kitsune_profile(slug, url, hide_browser_ui=hide_ui)

    # 2. Setup link router if requested
    if route_links:
        setup_link_router(profile_dir)

    # 3. Save icon
    icon_path = save_app_icon(slug, icon)

    # 4. Create desktop launcher (passing URL explicitly)
    desktop_file = create_desktop_launcher(
        slug=slug,
        name=name,
        url=url,
        profile_dir=profile_dir,
        icon_path=icon_path,
        description=description,
        categories=categories,
    )

    # 5. Pin to dock
    pinned = False
    if pin_dock:
        pinned = pin_to_gnome_dock(desktop_file.name)

    return {
        "slug": slug,
        "name": name,
        "url": url,
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
    ff_dir = get_firefox_dir()
    results = []

    for df in sorted(apps_dir.glob("kitsune-*.desktop")):
        slug = df.stem.replace("kitsune-", "")
        profile_dir = ff_dir / f"kitsune-{slug}"
        
        name = slug.capitalize()
        url = "N/A"

        # Parse basic desktop metadata
        try:
            with open(df, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("Name=") and not line.startswith("Name=Open"):
                        name = line.split("=", 1)[1].strip()
        except Exception:
            pass

        # Parse URL from user.js if available
        user_js = profile_dir / "user.js"
        if user_js.exists():
            try:
                with open(user_js, "r", encoding="utf-8") as f:
                    for line in f:
                        if 'user_pref("browser.startup.homepage"' in line:
                            match = re.search(r'"browser\.startup\.homepage",\s*"([^"]+)"', line)
                            if match:
                                url = match.group(1)
            except Exception:
                pass

        results.append({
            "slug": slug,
            "name": name,
            "url": url,
            "profile_dir": str(profile_dir),
            "desktop_file": str(df),
        })

    return results


def remove_app(slug: str) -> bool:
    """
    Uninstalls a Kitsune web application and cleans up all associated files.
    """
    apps_dir = get_applications_dir()
    icons_dir = get_icons_dir()
    ff_dir = get_firefox_dir()

    desktop_filename = f"kitsune-{slug}.desktop"
    desktop_file = apps_dir / desktop_filename
    profile_dir = ff_dir / f"kitsune-{slug}"

    # 1. Unpin from dock
    unpin_from_gnome_dock(desktop_filename)

    # 2. Remove desktop file
    if desktop_file.exists():
        desktop_file.unlink()

    # 3. Remove icon files
    for icon_file in icons_dir.glob(f"kitsune-{slug}.*"):
        try:
            icon_file.unlink()
        except Exception:
            pass

    # 4. Remove profile folder
    if profile_dir.exists():
        try:
            shutil.rmtree(profile_dir)
        except Exception:
            pass

    return True
