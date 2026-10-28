import base64
import json
import importlib.util
from pathlib import Path
import unittest
import tempfile
import subprocess
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("update", Path(__file__).resolve().parents[1] / "scripts/update.py")
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


def release(tag, date="2026-10-11T00:00:00Z", prerelease=True):
    return {"tag_name": tag, "published_at": date, "prerelease": prerelease, "draft": False,
            "assets": [{"name": f"T3-Code-{tag[1:]}-{arch}.AppImage", "size": 100,
                        "browser_download_url": f"https://github.com/pingdotgg/t3code/releases/download/{tag}/T3-Code-{tag[1:]}-{arch}.AppImage"}
                       for arch in update.ARCHES.values()]}


class UpdateTests(unittest.TestCase):
    def test_nightly_ignores_preview_and_release_list_order(self):
        old = release("v1.2.3-nightly.20261010.1", "2026-10-10T00:00:00Z")
        new = release("v1.2.3-nightly.20261011.2")
        preview = release("v1.2.3-preview.20261012.3", "2026-10-12T00:00:00Z")
        self.assertEqual(update.select_release([preview, old, new], "nightly"), new)

    def test_stable_excludes_prereleases_and_drafts(self):
        stable = release("v1.2.3", prerelease=False)
        draft = release("v1.2.4", "2026-10-12T00:00:00Z", False)
        draft["draft"] = True
        self.assertEqual(update.select_release([release("v1.2.4-nightly.20261012.1"), draft, stable], "stable"), stable)

    def test_missing_channel_fails(self):
        with self.assertRaises(ValueError):
            update.select_release([release("v1.2.3-preview.1")], "nightly")

    def test_missing_or_duplicate_asset_fails(self):
        item = release("v1.2.3", prerelease=False)
        item["assets"].pop()
        with self.assertRaises(ValueError):
            update.asset_urls(item)
        item = release("v1.2.3", prerelease=False)
        item["assets"].append(item["assets"][0])
        with self.assertRaises(ValueError):
            update.asset_urls(item)

    def test_foreign_or_empty_asset_fails(self):
        for field, value in [("browser_download_url", "https://example.com/payload"), ("size", 0)]:
            item = release("v1.2.3", prerelease=False)
            item["assets"][0][field] = value
            with self.assertRaises(ValueError):
                update.asset_urls(item)

    def test_cli_assets_require_both_architectures_and_exact_urls(self):
        item = release("v1.2.3", prerelease=False)
        for arch in ("x64", "arm64"):
            name = f"t3-1.2.3-linux-{arch}.tar.gz"
            item["assets"].append({"name": name, "size": 100,
                                   "browser_download_url": f"https://github.com/pingdotgg/t3code/releases/download/v1.2.3/{name}"})
        self.assertEqual(set(update.asset_urls(item, cli=True)), set(update.ARCHES))
        item["assets"][-1]["browser_download_url"] = "https://example.com/runtime.tar.gz"
        with self.assertRaises(ValueError):
            update.asset_urls(item, cli=True)

    def test_cli_checksums_are_required_and_must_match(self):
        item = release("v1.2.3", prerelease=False)
        for arch in ("x64", "arm64"):
            name = f"t3-1.2.3-linux-{arch}.tar.gz"
            item["assets"].append({"name": name, "browser_download_url": f"https://github.com/pingdotgg/t3code/releases/download/v1.2.3/{name}"})
        sri = "sha256-" + base64.b64encode(bytes(32)).decode()
        prefetch = subprocess.CompletedProcess([], 0, json.dumps({"hash": sri}))
        with patch.object(update.subprocess, "run", return_value=prefetch), self.assertRaisesRegex(ValueError, "require SHA256SUMS"):
            update.resolve(item)
        item["assets"].append({"name": "SHA256SUMS", "browser_download_url": "https://github.com/pingdotgg/t3code/releases/download/v1.2.3/SHA256SUMS"})
        for manifest, error in [("", "Missing checksum"), ("ff" * 32 + "  t3-1.2.3-linux-x64.tar.gz", "Checksum mismatched")]:
            def run(cmd, **kwargs):
                return subprocess.CompletedProcess(cmd, 0, manifest) if cmd[0] == "curl" else prefetch
            with patch.object(update.subprocess, "run", side_effect=run), self.assertRaisesRegex(ValueError, error):
                update.resolve(item)

    def test_prefetch_failure_does_not_write_partial_pins(self):
        stable = release("v1.2.3", prerelease=False)
        nightly = release("v1.2.4-nightly.20261011.1")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "releases.json"
            target.write_text("original pins")
            with patch.object(update, "ROOT", root), patch.object(update, "api", side_effect=[stable, [nightly]]), patch.object(update, "resolve", side_effect=[{}, subprocess.CalledProcessError(1, "nix")]):
                with self.assertRaises(subprocess.CalledProcessError):
                    update.main()
            self.assertEqual(target.read_text(), "original pins")


if __name__ == "__main__":
    unittest.main()
