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
import json
import os
import struct
import subprocess
import sys
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

            # Directly target the main user profile
            if main_profile_path and os.path.exists(main_profile_path):
                subprocess.Popen([
                    'firefox',
                    '--profile', main_profile_path,
                    '--new-tab', url
                ], env=clean_env, start_new_session=True)
            else:
                subprocess.Popen(['xdg-open', url], env=clean_env, start_new_session=True)

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
