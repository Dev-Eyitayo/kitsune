"""
Desktop entry, icon downloading, and shortcut integration for kitsune across Linux and Windows.
"""

import ast
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Optional


def is_windows() -> bool:
    return sys.platform == "win32"


def get_icons_dir() -> Path:
    if is_windows():
        d = Path(os.environ.get("APPDATA", Path.home())) / "kitsune" / "icons"
    else:
        d = Path.home() / ".local" / "share" / "icons"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_applications_dir() -> Path:
    if is_windows():
        d = Path(os.environ.get("APPDATA", Path.home())) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "kitsune"
    else:
        d = Path.home() / ".local" / "share" / "applications"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_app_icon(slug: str, icon_source: Optional[str] = None) -> Path:
    """
    Saves a mobile-grade squircle app icon.
    Prioritizes authentic bundled brand SVGs in assets/icons/.
    """
    icons_dir = get_icons_dir()
    ext = "ico" if is_windows() and icon_source and icon_source.endswith(".ico") else "svg"
    target_icon = icons_dir / f"kitsune-{slug}.{ext}"

    # 1. Check if a high-fidelity bundled icon exists in assets/icons/
    bundled_icon = Path(__file__).resolve().parent / "assets" / "icons" / f"{slug}.svg"
    if not bundled_icon.exists():
        bundled_icon = Path(__file__).resolve().parent.parent / "assets" / "icons" / f"{slug}.svg"
    if bundled_icon.exists():
        shutil.copy2(bundled_icon, target_icon)
        return target_icon

    # 2. If it's a local file path
    if icon_source and not icon_source.startswith(("http://", "https://")):
        src_path = Path(icon_source).expanduser()
        if src_path.exists():
            target = icons_dir / f"kitsune-{slug}{src_path.suffix}"
            shutil.copy2(src_path, target)
            return target

    # 3. If it's a remote URL
    if icon_source and icon_source.startswith(("http://", "https://")):
        detected_ext = "svg" if ".svg" in icon_source.lower() else ("ico" if ".ico" in icon_source.lower() else "png")
        target = icons_dir / f"kitsune-{slug}.{detected_ext}"
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
    with open(target_icon, "w", encoding="utf-8") as f:
        f.write(fallback_svg)
    return target_icon


def create_desktop_launcher(
    slug: str,
    name: str,
    url: str,
    launch_command: str,
    icon_path: Path,
    description: str = "",
    categories: str = "Network;WebBrowser;"
) -> Path:
    """
    Generates a Linux .desktop file or Windows .lnk Start Menu shortcut.
    """
    apps_dir = get_applications_dir()

    if is_windows():
        # Windows: Create .lnk shortcut in Start Menu
        shortcut_file = apps_dir / f"{name}.lnk"
        create_windows_shortcut(
            shortcut_path=str(shortcut_file),
            launch_command=launch_command,
            icon_path=str(icon_path),
            description=description or f"{name} Web App via Kitsune",
        )
        return shortcut_file

    # Linux: Create .desktop file
    desktop_file = apps_dir / f"kitsune-{slug}.desktop"
    wm_class = f"kitsune-{slug}"

    content = f"""[Desktop Entry]
Version=1.0
Name={name}
GenericName={name} Web App
Comment={description or f'{name} Web App via Kitsune'}
Exec={launch_command}
Icon={icon_path}
Terminal=false
Type=Application
StartupWMClass={wm_class}
StartupNotify=true
Categories={categories}
Actions=new-window;

[Desktop Action new-window]
Name=Open {name}
Exec={launch_command}
"""
    with open(desktop_file, "w", encoding="utf-8") as f:
        f.write(content)

    desktop_file.chmod(0o755)

    # Refresh desktop database
    try:
        subprocess.run(
            ["update-desktop-database", str(apps_dir)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

    return desktop_file


def create_windows_shortcut(shortcut_path: str, launch_command: str, icon_path: str, description: str):
    """Creates a Windows .lnk shortcut via PowerShell COM object."""
    # Split binary and args
    parts = launch_command.split(" ", 1)
    target_exe = parts[0].strip('"')
    args = parts[1] if len(parts) > 1 else ""

    ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target_exe}"
$Shortcut.Arguments = '{args}'
$Shortcut.Description = "{description}"
if (Test-Path "{icon_path}") {{
    $Shortcut.IconLocation = "{icon_path}"
}}
$Shortcut.Save()
"""
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def pin_to_gnome_dock(desktop_filename: str) -> bool:
    """
    Pins the .desktop launcher to Ubuntu GNOME Shell dock and Linux Mint Cinnamon favorites.
    """
    if is_windows():
        return True

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
    if is_windows():
        return True

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
