#!/usr/bin/env python3
"""Resolve channels, prefetch immutable assets, and atomically update both pins."""
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com/repos/pingdotgg/t3code"
ARCHES = {"x86_64-linux": "x86_64", "aarch64-linux": "arm64"}


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "t3code-nix-updater"}
    if token := os.environ.get("GH_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(API + path, headers=headers), timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
        time.sleep(2 ** attempt)


def select_release(releases, channel):
    pattern = r"v\d+\.\d+\.\d+" if channel == "stable" else r"v\d+\.\d+\.\d+-nightly\.\d+\.\d+"
    candidates = [r for r in releases if not r.get("draft", False)
                  and bool(r["prerelease"]) == (channel == "nightly")
                  and re.fullmatch(pattern, r["tag_name"])]
    if not candidates:
        raise ValueError(f"No {channel} release found")
    return max(candidates, key=lambda r: r["published_at"])


def asset_urls(release):
    version = release["tag_name"].removeprefix("v")
    urls = {}
    for system, arch in ARCHES.items():
        name = f"T3-Code-{version}-{arch}.AppImage"
        matches = [a for a in release["assets"] if a["name"] == name and a.get("size", 1) > 0]
        if len(matches) != 1:
            raise ValueError(f"Expected one nonempty {name} asset")
        url = matches[0]["browser_download_url"]
        if url != f"https://github.com/pingdotgg/t3code/releases/download/{release['tag_name']}/{name}":
            raise ValueError(f"Unexpected asset URL: {url}")
        urls[system] = url
    return urls


def resolve(release):
    assets = {}
    checksums = next((a for a in release["assets"] if a["name"] == "SHA256SUMS"), None)
    expected = {}
    if checksums:
        url = checksums["browser_download_url"]
        if not url.startswith(f"https://github.com/pingdotgg/t3code/releases/download/{release['tag_name']}/"):
            raise ValueError("Unexpected checksum URL")
        result = subprocess.run(["curl", "--fail", "--location", "--retry", "3", url], check=True, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) == 2 and re.fullmatch(r"[a-fA-F0-9]{64}", parts[0]):
                expected[parts[1].lstrip("*")] = parts[0].lower()
    for system, url in asset_urls(release).items():
        result = subprocess.run(["nix", "store", "prefetch-file", "--json", url], check=True, capture_output=True, text=True)
        sri = json.loads(result.stdout)["hash"]
        if checksums:
            name = url.rsplit("/", 1)[1]
            actual = base64.b64decode(sri.removeprefix("sha256-")).hex()
            if name in expected and expected[name] != actual:
                raise ValueError(f"Checksum mismatched for {name}")
        assets[system] = {"url": url, "hash": sri}
    return {"version": release["tag_name"].removeprefix("v"), "assets": assets}


def main():
    stable = select_release([api("/releases/latest")], "stable")
    # GitHub release ordering is not publication ordering; scan several pages.
    releases = []
    for page in range(1, 6):
        batch = api(f"/releases?per_page=100&page={page}")
        releases.extend(batch)
        if len(batch) < 100:
            break
    nightly = select_release(releases, "nightly")
    pins = {"stable": resolve(stable), "nightly": resolve(nightly)}
    content = json.dumps(pins, indent=2) + "\n"
    target = ROOT / "releases.json"
    if target.exists() and target.read_text() == content:
        print("Release pins already current")
        return
    with tempfile.NamedTemporaryFile(mode="w", dir=ROOT, delete=False) as stream:
        stream.write(content)
        temporary = Path(stream.name)
    temporary.replace(target)
    print(f"Updated stable={pins['stable']['version']} nightly={pins['nightly']['version']}")


if __name__ == "__main__":
    main()
