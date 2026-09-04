"""
Core orchestration logic for kitsune.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def translate_protocol_url(slug: str, url: str) -> str:
    """Translates incoming URI schemes and action links into Web App URLs."""
    if not url:
        return ""
    url = url.strip()

    if slug == "whatsapp":
        from urllib.parse import urlparse, parse_qs
        try:
            u = urlparse(url)
            params = parse_qs(u.query)

            # 1. Channel invite code (from web accept links or queries)
            channel_code = params.get("channel_invite_code", [""])[0]
            if channel_code:
                return f"https://web.whatsapp.com/channel/{channel_code}"

            if u.scheme == "whatsapp":
                net = (u.netloc or "").lower()
                path = (u.path or "").strip("/").lower()
                if "channel" in net or "channel" in path:
                    ch = params.get("id", [""])[0] or u.path.strip("/").split("/")[-1]
                    return f"https://web.whatsapp.com/channel/{ch}" if ch else "https://web.whatsapp.com"
                elif net == "chat" or path == "chat":
                    code = params.get("code", [""])[0]
                    return f"https://web.whatsapp.com/accept?code={code}" if code else "https://web.whatsapp.com"
                elif net == "send" or path == "send":
                    phone = params.get("phone", [""])[0]
                    text = params.get("text", [""])[0]
                    q = []
                    if phone:
                        q.append(f"phone={phone}")
                    if text:
                        q.append(f"text={text}")
                    qs = "&".join(q)
                    return f"https://web.whatsapp.com/send?{qs}" if qs else "https://web.whatsapp.com"
            elif "whatsapp.com" in (u.netloc or ""):
                if "/channel/" in u.path:
                    ch_id = u.path.split("/channel/")[-1].strip("/")
                    return f"https://web.whatsapp.com/channel/{ch_id}"
                elif "chat.whatsapp.com" in u.netloc:
                    code = u.path.strip("/")
                    return f"https://web.whatsapp.com/accept?code={code}"
            elif "wa.me" in (u.netloc or ""):
                phone = u.path.strip("/")
                q = u.query
                return f"https://web.whatsapp.com/send?phone={phone}&{q}" if q else f"https://web.whatsapp.com/send?phone={phone}"
        except Exception:
            pass
    return url


def launch_app(slug: str, url_arg: Optional[str] = None) -> bool:
    """Launches an app or dispatches an incoming URL to its running instance."""
    ff_dir = get_firefox_dir()
    profile_dir = ff_dir / f"kitsune-{slug}"
    if not profile_dir.exists():
        return False

    target_url = translate_protocol_url(slug, url_arg or "")
    if not target_url:
        preset = PRESETS.get(slug)
        target_url = preset["url"] if preset else f"https://{slug}.com"

    wm_class = f"kitsune-{slug}"
    cmd = [
        "firefox",
        "--class", wm_class,
        "--name", wm_class,
        "--profile", str(profile_dir),
        target_url
    ]
    import os
    env = os.environ.copy()
    env["GDK_BACKEND"] = "x11"
    env["MOZ_APP_REMOTINGNAME"] = wm_class

    subprocess.Popen(cmd, env=env, start_new_session=True)
    return True


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
    Creates a standalone web app with dedicated profile, desktop launcher, and dock integration.
    """
    if not slug:
        slug = slugify(name)

    preset = PRESETS.get(slug, {})
    mime_types = preset.get("mime_types")

    # 1. Create/update dedicated Firefox profile (never deletes existing cookies/data)
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
        mime_types=mime_types,
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


def refresh_all_apps() -> List[Dict[str, str]]:
    """
    Refreshes all installed web apps with the latest userChrome.css, user.js,
    and desktop launcher configurations.
    """
    apps = list_apps()
    refreshed = []
    for app in apps:
        slug = app["slug"]
        url = app["url"]
        name = app["name"]
        if url and url != "N/A":
            create_app(
                name=name,
                url=url,
                slug=slug,
                pin_dock=False,
                route_links=True,
                hide_ui=True
            )
            refreshed.append(app)
    return refreshed


def update_kitsune() -> Dict[str, Any]:
    """
    Updates kitsune codebase from GitHub and refreshes all installed web applications.
    """
    repo_url = "https://github.com/dev-eyitayo/kitsune.git"
    install_dir = Path.home() / ".local" / "share" / "kitsune"
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
