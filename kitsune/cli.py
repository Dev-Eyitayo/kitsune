"""
Command Line Interface and Interactive Wizard for kitsune.
"""

import argparse
import sys
from typing import Optional

from . import __version__
from .core import create_app, list_apps, refresh_all_apps, remove_app, update_kitsune
from .presets import PRESETS


class Colors:
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_banner():
    banner = f"""{Colors.CYAN}{Colors.BOLD}
  ██╗  ██╗██╗████████╗███████╗██╗   ██╗███╗   ██╗███████╗
  ██║ ██╔╝██║╚══██╔══╝██╔════╝██║   ██║████╗  ██║██╔════╝
  █████╔╝ ██║   ██║   ███████╗██║   ██║██╔██╗ ██║█████╗  
  ██╔═██╗ ██║   ██║   ╚════██║██║   ██║██║╚██╗██║██╔══╝  
  ██║  ██╗██║   ██║   ███████║╚██████╔╝██║ ╚████║███████╗
  ╚═╝  ╚═╝╚═╝   ╚═╝   ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝
{Colors.RESET}{Colors.BLUE}  Firefox Web App & Desktop Integration Tool for Linux (v{__version__}){Colors.RESET}
"""
    print(banner)


def prompt_bool(prompt_text: str, default: bool = True) -> bool:
    choice = "[Y/n]" if default else "[y/N]"
    val = input(f"{Colors.BOLD}{prompt_text}{Colors.RESET} {choice}: ").strip().lower()
    if not val:
        return default
    return val.startswith("y")


def interactive_create():
    print(f"\n{Colors.BOLD}Create a New Desktop Web Application{Colors.RESET}")
    print(f"{Colors.BLUE}Available presets: whatsapp, chatgpt, claude, discord, notion, spotify, slack, messages, youtube-music, x, github{Colors.RESET}\n")

    name_or_preset = input(f"{Colors.BOLD}Application Name (or preset):{Colors.RESET} ").strip()
    if not name_or_preset:
        print(f"{Colors.RED}Error: Application name cannot be empty.{Colors.RESET}")
        return

    preset_key = name_or_preset.lower().replace(" ", "-")
    preset = PRESETS.get(preset_key)

    if preset:
        print(f"\n{Colors.GREEN}[OK] Loaded built-in preset for '{preset['name']}'{Colors.RESET}")
        name = preset["name"]
        default_url = preset["url"]
        default_icon = preset["icon_url"]
        default_categories = preset.get("categories", "Network;WebBrowser;")
        default_desc = preset.get("description", "")
    else:
        name = name_or_preset
        default_url = ""
        default_icon = ""
        default_categories = "Network;WebBrowser;"
        default_desc = f"{name} Web App via Kitsune"

    url_prompt = f"Web App URL (e.g. https://...)" if not default_url else f"Web App URL [{default_url}]"
    url = input(f"{Colors.BOLD}{url_prompt}:{Colors.RESET} ").strip() or default_url
    if not url:
        print(f"{Colors.RED}Error: URL is required.{Colors.RESET}")
        return

    icon_prompt = "Icon (URL or local path)" if not default_icon else f"Icon URL/Path [{default_icon}]"
    icon = input(f"{Colors.BOLD}{icon_prompt}:{Colors.RESET} ").strip() or default_icon

    pin_dock = prompt_bool("Pin to Ubuntu Dock / Favorites?", default=True)
    route_links = prompt_bool("Route clicked external links to main Firefox browser?", default=True)
    hide_ui = prompt_bool("Hide browser toolbar & address bar for native app feel?", default=True)

    print(f"\n{Colors.CYAN}Configuring {name}...{Colors.RESET}")
    info = create_app(
        name=name,
        url=url,
        icon=icon,
        description=default_desc,
        categories=default_categories,
        pin_dock=pin_dock,
        route_links=route_links,
        hide_ui=hide_ui,
    )

    print(f"\n{Colors.GREEN}{Colors.BOLD}[OK] Successfully created {name}{Colors.RESET}")
    print(f"  - Profile Directory: {Colors.BLUE}{info['profile_dir']}{Colors.RESET}")
    print(f"  - Desktop Launcher:  {Colors.BLUE}{info['desktop_file']}{Colors.RESET}")
    print(f"  - Icon Path:         {Colors.BLUE}{info['icon_path']}{Colors.RESET}")
    if info["pinned"] == "True":
        print(f"  - Dock Status:       {Colors.GREEN}Pinned to Ubuntu Dock{Colors.RESET}")
    print(f"\nYou can now launch {name} directly from your dock or application menu.\n")


def cmd_create(args):
    # If no arguments provided, launch wizard
    if not args.name and not args.url:
        interactive_create()
        return

    name = args.name
    preset_key = name.lower().replace(" ", "-") if name else ""
    preset = PRESETS.get(preset_key)

    url = args.url or (preset["url"] if preset else None)
    if not url:
        print(f"{Colors.RED}Error: URL is required. Use --url <URL>{Colors.RESET}")
        return

    app_name = preset["name"] if preset and not args.name_override else (args.name_override or name)
    icon = args.icon or (preset["icon_url"] if preset else None)
    categories = preset.get("categories", "Network;WebBrowser;") if preset else "Network;WebBrowser;"
    desc = preset.get("description", "") if preset else f"{app_name} Web App via Kitsune"

    print(f"{Colors.CYAN}Creating web app '{app_name}'...{Colors.RESET}")
    info = create_app(
        name=app_name,
        url=url,
        icon=icon,
        description=desc,
        categories=categories,
        pin_dock=not args.no_pin,
        route_links=not args.no_route,
        hide_ui=not args.show_ui,
    )
    print(f"{Colors.GREEN}{Colors.BOLD}[OK] Created {app_name}{Colors.RESET} (Pinned to dock: {info['pinned']})")


def cmd_list(args):
    apps = list_apps()
    if not apps:
        print(f"{Colors.YELLOW}No Kitsune web applications found.{Colors.RESET}")
        print(f"Run {Colors.BOLD}kitsune create{Colors.RESET} to create your first web app.")
        return

    print(f"\n{Colors.BOLD}{Colors.CYAN}Installed Kitsune Web Applications ({len(apps)}):{Colors.RESET}\n")
    for app in apps:
        print(f"  [x] {Colors.BOLD}{app['name']}{Colors.RESET} ({Colors.BLUE}{app['slug']}{Colors.RESET})")
        print(f"      URL:      {app['url']}")
        print(f"      Launcher: {app['desktop_file']}")
        print(f"      Profile:  {app['profile_dir']}")
        print()


def cmd_remove(args):
    slug = args.slug.lower().strip()
    print(f"{Colors.YELLOW}Removing web app '{slug}'...{Colors.RESET}")
    remove_app(slug)
    print(f"{Colors.GREEN}[OK] Successfully removed {slug} and cleaned up all files.{Colors.RESET}")


def cmd_presets(args):
    print(f"\n{Colors.BOLD}{Colors.CYAN}Available Built-in Presets:{Colors.RESET}\n")
    for key, p in PRESETS.items():
        print(f"  {Colors.BOLD}{key:<16}{Colors.RESET} -> {p['name']:<18} ({p['url']})")
    print(f"\nUsage: {Colors.BOLD}kitsune create <preset-name>{Colors.RESET} (e.g. kitsune create whatsapp)\n")


def cmd_update(args):
    print(f"\n{Colors.CYAN}[INFO] Checking for updates and pulling latest kitsune release...{Colors.RESET}")
    res = update_kitsune()
    if res["updated_code"]:
        print(f"{Colors.GREEN}[OK] Successfully updated kitsune codebase.{Colors.RESET}")
    else:
        print(f"{Colors.BLUE}[INFO] Kitsune codebase is up to date.{Colors.RESET}")

    apps = res["refreshed_apps"]
    if apps:
        print(f"\n{Colors.CYAN}[INFO] Refreshing {len(apps)} installed web application(s)...{Colors.RESET}")
        for app in apps:
            print(f"  {Colors.GREEN}[OK]{Colors.RESET} Refreshed: {Colors.BOLD}{app['name']}{Colors.RESET} ({app['slug']})")
        print(f"\n{Colors.GREEN}{Colors.BOLD}[OK] All web apps refreshed with latest fixes!{Colors.RESET}\n")
    else:
        print(f"\n{Colors.YELLOW}[INFO] No installed web apps found to refresh.{Colors.RESET}\n")


def cmd_refresh(args):
    apps = refresh_all_apps()
    if not apps:
        print(f"{Colors.YELLOW}No installed web applications found to refresh.{Colors.RESET}")
        return

    print(f"\n{Colors.CYAN}[INFO] Refreshing {len(apps)} installed web application(s)...{Colors.RESET}")
    for app in apps:
        print(f"  {Colors.GREEN}[OK]{Colors.RESET} Refreshed: {Colors.BOLD}{app['name']}{Colors.RESET} ({app['slug']})")
    print(f"\n{Colors.GREEN}{Colors.BOLD}[OK] All web apps successfully refreshed!{Colors.RESET}\n")


def main():
    parser = argparse.ArgumentParser(
        prog="kitsune",
        description="Turn any website into a standalone desktop web app using Firefox on Linux.",
    )
    parser.add_argument("-v", "--version", action="version", version=f"kitsune {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Create command
    create_p = subparsers.add_parser("create", help="Create a new web application")
    create_p.add_argument("name", nargs="?", help="App name or preset (e.g. whatsapp, chatgpt, discord)")
    create_p.add_argument("--url", help="Web App URL")
    create_p.add_argument("--name", dest="name_override", help="Custom display name")
    create_p.add_argument("--icon", help="Icon file path or download URL")
    create_p.add_argument("--no-pin", action="store_true", help="Do not pin to Ubuntu dock")
    create_p.add_argument("--no-route", action="store_true", help="Do not route external links to main browser")
    create_p.add_argument("--show-ui", action="store_true", help="Keep standard browser URL bar and tabs")

    # List command
    subparsers.add_parser("list", help="List all installed Kitsune web applications")

    # Remove command
    remove_p = subparsers.add_parser("remove", help="Remove an installed web application")
    remove_p.add_argument("slug", help="Slug of the app to remove (e.g. whatsapp, chatgpt)")

    # Presets command
    subparsers.add_parser("presets", help="List all available presets")

    # Update command
    subparsers.add_parser("update", help="Update kitsune and refresh all installed web apps")

    # Refresh command
    subparsers.add_parser("refresh", help="Refresh configuration for all installed web apps")

    args = parser.parse_args()

    if not args.command:
        print_banner()
        parser.print_help()
        print()
        interactive_create()
        return

    if args.command == "create":
        cmd_create(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "remove":
        cmd_remove(args)
    elif args.command == "presets":
        cmd_presets(args)
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "refresh":
        cmd_refresh(args)


if __name__ == "__main__":
    main()
