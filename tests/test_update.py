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
