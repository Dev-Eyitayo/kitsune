"""
Desktop entry, icon downloading, and Linux desktop (GNOME, Cinnamon, MATE) dock integration for kitsune.
"""

import ast
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional


def get_icons_dir() -> Path:
    d = Path.home() / ".local" / "share" / "icons"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_applications_dir() -> Path:
    d = Path.home() / ".local" / "share" / "applications"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_app_icon(slug: str, icon_source: Optional[str] = None) -> Path:
    """
    Saves a mobile-grade squircle app icon to ~/.local/share/icons/.
    Prioritizes authentic bundled brand SVGs in assets/icons/.
    """
    icons_dir = get_icons_dir()
    target_svg = icons_dir / f"kitsune-{slug}.svg"

    # 1. Check if a high-fidelity bundled icon exists in assets/icons/
    bundled_icon = Path(__file__).resolve().parent / "assets" / "icons" / f"{slug}.svg"
    if not bundled_icon.exists():
        bundled_icon = Path(__file__).resolve().parent.parent / "assets" / "icons" / f"{slug}.svg"
    if bundled_icon.exists():
        shutil.copy2(bundled_icon, target_svg)
        return target_svg

    # 2. If it's a local file path
    if icon_source and not icon_source.startswith(("http://", "https://")):
        src_path = Path(icon_source).expanduser()
        if src_path.exists():
            target = icons_dir / f"kitsune-{slug}{src_path.suffix}"
            shutil.copy2(src_path, target)
            return target

    # 3. If it's a remote URL
    if icon_source and icon_source.startswith(("http://", "https://")):
        ext = "svg" if ".svg" in icon_source.lower() else "png"
        target = icons_dir / f"kitsune-{slug}.{ext}"
        try:
            req = urllib.request.Request(icon_source, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp, open(target, "wb") as f:
                f.write(resp.read())
            return target
        except Exception:
            pass

    # 4. Fallback: Clean modern mobile-style squircle with initial letter
    initial = (slug[0] if slug else "K").upper()
    fallback_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="fallbackGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ff7e40"/>
      <stop offset="100%" stop-color="#e65100"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="115" fill="url(#fallbackGrad)"/>
  <text x="256" y="330" font-size="220" text-anchor="middle" fill="#ffffff" font-family="sans-serif" font-weight="bold">{initial}</text>
</svg>"""
    with open(target_svg, "w", encoding="utf-8") as f:
        f.write(fallback_svg)
    return target_svg


def create_desktop_launcher(
    slug: str,
    name: str,
    url: str,
    profile_dir: Path,
    icon_path: Path,
    description: str = "",
    categories: str = "Network;WebBrowser;",
    mime_types: Optional[str] = None
) -> Path:
    """
    Generates the .desktop launcher file configured for GNOME / Wayland / XWayland / X11 dock separation.
    """
    apps_dir = get_applications_dir()
    desktop_file = apps_dir / f"kitsune-{slug}.desktop"
    
    wm_class = f"kitsune-{slug}"
    kitsune_bin = shutil.which("kitsune") or "kitsune"
    
    mime_line = f"MimeType={mime_types}\n" if mime_types else ""
    if mime_types:
        exec_cmd = f"{kitsune_bin} launch {slug} %u"
    else:
        exec_cmd = f'env GDK_BACKEND=x11 MOZ_APP_REMOTINGNAME={wm_class} firefox --class {wm_class} --name {wm_class} --new-instance --profile "{profile_dir}" "{url}"'
    
    content = f"""[Desktop Entry]
Version=1.0
Name={name}
GenericName={name} Web App
Comment={description or f'{name} Web App via Kitsune'}
Exec={exec_cmd}
Icon={icon_path}
Terminal=false
Type=Application
StartupWMClass={wm_class}
StartupNotify=true
Categories={categories}
{mime_line}Actions=new-window;

[Desktop Action new-window]
Name=Open {name}
Exec={exec_cmd}
"""
    with open(desktop_file, "w", encoding="utf-8") as f:
        f.write(content)

    desktop_file.chmod(0o755)

    # Register MIME / Scheme handlers if present
    if mime_types:
        for mt in mime_types.split(";"):
            mt = mt.strip()
            if mt:
                try:
                    subprocess.run(["xdg-mime", "default", desktop_file.name, mt], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass

    # Refresh desktop database
    try:
        subprocess.run(["update-desktop-database", str(apps_dir)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    return desktop_file


def pin_to_gnome_dock(desktop_filename: str) -> bool:
    """
    Pins the .desktop launcher to Ubuntu GNOME Shell dock and Linux Mint Cinnamon favorites.
    """
    pinned = False
    
    # 1. GNOME Shell (Ubuntu, Fedora, Debian GNOME)
    try:
        res = subprocess.run(
            ["gsettings", "get", "org.gnome.shell", "favorite-apps"],
            capture_output=True,
            text=True,
            check=True
        )
        current_favorites = ast.literal_eval(res.stdout.strip())
        if desktop_filename not in current_favorites:
            current_favorites.append(desktop_filename)
            subprocess.run(
                ["gsettings", "set", "org.gnome.shell", "favorite-apps", str(current_favorites)],
                check=True
            )
        pinned = True
    except Exception:
        pass

    # 2. Cinnamon (Linux Mint)
    try:
        res = subprocess.run(
            ["gsettings", "get", "org.cinnamon", "favorite-apps"],
            capture_output=True,
            text=True,
            check=True
        )
        current_favorites = ast.literal_eval(res.stdout.strip())
        if desktop_filename not in current_favorites:
            current_favorites.append(desktop_filename)
            subprocess.run(
                ["gsettings", "set", "org.cinnamon", "favorite-apps", str(current_favorites)],
                check=True
            )
        pinned = True
    except Exception:
        pass

    return pinned


def unpin_from_gnome_dock(desktop_filename: str) -> bool:
    """
    Removes the .desktop launcher from GNOME Shell dock and Linux Mint Cinnamon favorites.
    """
    unpinned = False

    # 1. GNOME Shell
    try:
        res = subprocess.run(
            ["gsettings", "get", "org.gnome.shell", "favorite-apps"],
            capture_output=True,
            text=True,
            check=True
        )
        current_favorites = ast.literal_eval(res.stdout.strip())
        if desktop_filename in current_favorites:
            current_favorites.remove(desktop_filename)
            subprocess.run(
                ["gsettings", "set", "org.gnome.shell", "favorite-apps", str(current_favorites)],
                check=True
            )
        unpinned = True
    except Exception:
        pass

    # 2. Cinnamon (Linux Mint)
    try:
        res = subprocess.run(
            ["gsettings", "get", "org.cinnamon", "favorite-apps"],
            capture_output=True,
            text=True,
            check=True
        )
        current_favorites = ast.literal_eval(res.stdout.strip())
        if desktop_filename in current_favorites:
            current_favorites.remove(desktop_filename)
            subprocess.run(
                ["gsettings", "set", "org.cinnamon", "favorite-apps", str(current_favorites)],
                check=True
            )
        unpinned = True
    except Exception:
        pass

    return unpinned
