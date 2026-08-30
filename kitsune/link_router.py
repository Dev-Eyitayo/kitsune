"""
Link routing subsystem for kitsune.
Intercepts external link clicks inside the web app and delegates them to the main Firefox profile.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from .profile import get_main_profile_path


ROUTER_SCRIPT_CONTENT = """#!/usr/bin/env python3
import ctypes
import json
import os
import shutil
import struct
import subprocess
import sys
import time
from ctypes import c_ulong, c_int, c_long, Structure, POINTER, byref
from urllib.parse import urlparse

AUTH_DOMAINS = [
    "accounts.google.com",
    "accounts.youtube.com",
    "appleid.apple.com",
    "login.microsoftonline.com",
    "login.live.com",
    "github.com",
    "auth0.com",
    "auth.atlassian.com",
    "okta.com",
    "onelogin.com",
    "pingidentity.com",
    "duosecurity.com",
    "stripe.com",
    "paypal.com",
    "paddle.com",
    "api.twitter.com",
    "twitter.com",
    "x.com",
    "t.co",
    "arkoselabs.com",
    "funcaptcha.com",
    "oauth.telegram.org",
    "discord.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "slack.com"
]

class XClientMessageEvent(Structure):
    _fields_ = [
        ('type', c_int),
        ('serial', c_ulong),
        ('send_event', c_int),
        ('display', ctypes.c_void_p),
        ('window', c_ulong),
        ('message_type', c_ulong),
        ('format', c_int),
        ('l', c_long * 5)
    ]

class XEvent(ctypes.Union):
    _fields_ = [
        ('type', c_int),
        ('xclient', XClientMessageEvent),
        ('pad', c_long * 24)
    ]

def raise_main_browser_window():
    try:
        x11 = ctypes.CDLL('libX11.so.6')
        display = x11.XOpenDisplay(None)
        if not display:
            return False
        
        root = x11.XDefaultRootWindow(display)
        net_client_list = x11.XInternAtom(display, b'_NET_CLIENT_LIST', False)
        net_active_window = x11.XInternAtom(display, b'_NET_ACTIVE_WINDOW', False)
        wm_class_atom = x11.XInternAtom(display, b'WM_CLASS', False)
        
        actual_type = c_ulong()
        actual_format = c_int()
        nitems = c_ulong()
        bytes_after = c_ulong()
        prop = ctypes.c_void_p()
        
        res = x11.XGetWindowProperty(
            display, root, net_client_list, 0, 1024, False, 33,
            byref(actual_type), byref(actual_format), byref(nitems), byref(bytes_after), byref(prop)
        )
        
        if res != 0 or not prop:
            x11.XCloseDisplay(display)
            return False
            
        windows = ctypes.cast(prop, POINTER(c_ulong))
        target_win = None
        
        for i in range(nitems.value):
            win = windows[i]
            class_prop = ctypes.c_void_p()
            c_nitems = c_ulong()
            x11.XGetWindowProperty(display, win, wm_class_atom, 0, 1024, False, 31, byref(actual_type), byref(actual_format), byref(c_nitems), byref(bytes_after), byref(class_prop))
            if class_prop:
                raw_bytes = ctypes.string_at(class_prop, c_nitems.value)
                parts = [p.decode('latin1', errors='ignore').lower() for p in raw_bytes.split(b'\\x00') if p]
                x11.XFree(class_prop)
                
                # Match main browser window (contains 'firefox', 'chrome', 'edge', etc. but NOT kitsune-*)
                if any('firefox' in p for p in parts) and not any(p.startswith('kitsune-') for p in parts):
                    target_win = win
                    break
        
        x11.XFree(prop)
        
        if target_win:
            event = XEvent()
            event.type = 33 # ClientMessage
            event.xclient.type = 33
            event.xclient.serial = 0
            event.xclient.send_event = 1
            event.xclient.display = display
            event.xclient.window = target_win
            event.xclient.message_type = net_active_window
            event.xclient.format = 32
            event.xclient.l[0] = 2 # 2 = Pager / user direct request (forces window manager to raise and focus)
            event.xclient.l[1] = 0
            event.xclient.l[2] = 0
            event.xclient.l[3] = 0
            event.xclient.l[4] = 0
            
            mask = (1 << 19) | (1 << 20)
            x11.XSendEvent(display, root, False, mask, byref(event))
            x11.XFlush(display)
            x11.XCloseDisplay(display)
            return True
        x11.XCloseDisplay(display)
        return False
    except Exception:
        return False

def is_auth_url(url_str):
    try:
        u = urlparse(url_str)
        host = (u.hostname or "").lower()
        if any(host == d or host.endswith("." + d) for d in AUTH_DOMAINS):
            if (
                host in ("accounts.google.com", "appleid.apple.com")
                or "/login" in u.path
                or "/oauth" in u.path
                or "/signin" in u.path
                or "/auth" in u.path
                or "/i/flow" in u.path
                or "client_id=" in u.query
                or "redirect_uri=" in u.query
            ):
                return True
        if "/oauth" in u.path or "client_id=" in u.query or "redirect_uri=" in u.query:
            return True
        return False
    except Exception:
        return False

def read_message():
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        return None
    message_length = struct.unpack('@I', raw_length)[0]
    raw_msg = sys.stdin.buffer.read(message_length).decode('utf-8')
    try:
        return json.loads(raw_msg)
    except Exception:
        return raw_msg.strip('"')

def main():
    clean_env = os.environ.copy()
    clean_env.pop('GDK_BACKEND', None)
    clean_env.pop('MOZ_APP_NAME', None)
    clean_env.pop('MOZ_APP_REMOTINGNAME', None)

    main_profile_path = os.environ.get("KITSUNE_MAIN_PROFILE", "{main_profile}")

    while True:
        data = read_message()
        if data is None:
            break
        url = None
        if isinstance(data, dict):
            url = data.get('url') or data.get('href')
        elif isinstance(data, str):
            url = data.strip()
        
        if url and isinstance(url, str) and url.startswith(('http://', 'https://', 'mailto:')):
            # Do not intercept OAuth, SSO, or payment authentication popups
            if is_auth_url(url):
                continue

            # Generate fresh XDG / FreeDesktop startup activation token
            launch_env = clean_env.copy()
            timestamp = int(time.time() * 1000)
            token = f"kitsune_{os.getpid()}_{timestamp}_TIME{timestamp}"
            launch_env["DESKTOP_STARTUP_ID"] = token
            # Dispatch through native GNOME / FreeDesktop URL handler so Ubuntu triggers desktop notification & focus
            if shutil.which("gio"):
                subprocess.Popen(['gio', 'open', url], env=launch_env, start_new_session=True)
            elif shutil.which("xdg-open"):
                subprocess.Popen(['xdg-open', url], env=launch_env, start_new_session=True)
            elif main_profile_path and os.path.exists(main_profile_path):
                subprocess.Popen([
                    'firefox',
                    '--profile', main_profile_path,
                    '--new-tab', url
                ], env=launch_env, start_new_session=True)

            # Also trigger active window raise if available
            raise_main_browser_window()

if __name__ == '__main__':
    main()
"""


def setup_link_router(profile_dir: Path) -> bool:
    """
    Installs the link routing extension and native messaging host.
    """
    main_profile = get_main_profile_path()
    
    # 1. Deploy the helper router script
    share_dir = Path.home() / ".local" / "share" / "kitsune"
    share_dir.mkdir(parents=True, exist_ok=True)
    router_script = share_dir / "router.py"
    
    with open(router_script, "w", encoding="utf-8") as f:
        f.write(ROUTER_SCRIPT_CONTENT.replace("{main_profile}", str(main_profile)))
    
    router_script.chmod(0o755)

    # 2. Register the native messaging host manifest
    native_hosts_dir = Path.home() / ".mozilla" / "native-messaging-hosts"
    native_hosts_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = native_hosts_dir / "pwalinks.json"
    
    manifest = {
        "name": "pwalinks",
        "description": "Kitsune External Link Router",
        "path": str(router_script),
        "type": "stdio",
        "allowed_extensions": ["@pwalinks"]
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # 3. Copy bundled extension into profile extensions directory
    bundled_xpi = Path(__file__).resolve().parent / "assets" / "extension" / "@pwalinks.xpi"
    if not bundled_xpi.exists():
        bundled_xpi = Path(__file__).resolve().parent.parent / "assets" / "extension" / "@pwalinks.xpi"
    target_extensions_dir = profile_dir / "extensions"
    target_extensions_dir.mkdir(parents=True, exist_ok=True)
    target_xpi = target_extensions_dir / "@pwalinks.xpi"

    if bundled_xpi.exists():
        shutil.copy2(bundled_xpi, target_xpi)
        return True
    return False
