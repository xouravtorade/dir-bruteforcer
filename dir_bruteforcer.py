#!/usr/bin/env python3
"""Small, rate-limited directory checker for authorized testing only."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from colorama import Fore, Style, init


REQUEST_DELAY_SECONDS = 0.5
REQUEST_TIMEOUT_SECONDS = 8
USER_AGENT = "AuthorizedDirectoryChecker/1.0"


def get_inputs() -> tuple[str, Path]:
    target = input("Enter target URL: ").strip()
    wordlist_name = input("Enter wordlist file: ").strip()

    if not target.startswith(("http://", "https://")):
        target = "http://" + target

    parsed = urlparse(target)
    if not parsed.netloc:
        raise ValueError("Please enter a valid URL, for example https://example.com")

    wordlist = Path(wordlist_name).expanduser()
    if not wordlist.is_file():
        raise FileNotFoundError(f"Wordlist not found: {wordlist}")

    return target.rstrip("/") + "/", wordlist


def load_paths(wordlist: Path) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()

    for line in wordlist.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        entry = entry.lstrip("/")
        if entry and entry not in seen:
            seen.add(entry)
            paths.append(entry)

    return paths


def scan(target: str, paths: list[str]) -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    print(f"\n[*] Checking {len(paths)} paths on {target}")
    print("[*] Delay: %.1fs between requests\n" % REQUEST_DELAY_SECONDS)

    found = 0
    for path in paths:
        url = urljoin(target, path)
        try:
            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                allow_redirects=False,
            )
            # 2xx means found; 3xx is reported because it may reveal a real route.
            if 200 <= response.status_code < 400:
                found += 1
                location = response.headers.get("Location")
                suffix = f" -> {location}" if location else ""
                print(
                    f"{Fore.GREEN}[+] Found: {url} "
                    f"[{response.status_code}, {len(response.content)} bytes]{suffix}"
                    f"{Style.RESET_ALL}"
                )
            else:
                print(f"[-] {response.status_code}: {url}")
        except requests.RequestException as exc:
            print(f"{Fore.YELLOW}[!] Error: {url} ({exc}){Style.RESET_ALL}")

        time.sleep(REQUEST_DELAY_SECONDS)

    print(f"\n[*] Finished. Found {found} possible path(s).")


def main() -> int:
    init(autoreset=True)
    print("Authorized Directory Checker")
    print("Use only on systems you own or have permission to test.\n")

    try:
        target, wordlist = get_inputs()
        paths = load_paths(wordlist)
        if not paths:
            print("The wordlist has no usable entries.")
            return 1
        scan(target, paths)
    except (ValueError, FileNotFoundError, OSError) as exc:
        print(f"{Fore.RED}[!] {exc}{Style.RESET_ALL}")
        return 1
    except KeyboardInterrupt:
        print("\n[!] Scan stopped.")
        return 130

    return 0


if __name__ == "__main__":
    sys.exit(main())