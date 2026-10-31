import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from scripts import prepare_malecns_data


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "malecns" / "raw-files.json"


class RawDataManifestTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_has_six_unique_official_inputs(self):
        files = self.payload["files"]
        self.assertEqual(len(files), 6)
        self.assertEqual(len({item["name"] for item in files}), 6)
        self.assertTrue(self.payload["base_url"].startswith("https://storage.googleapis.com/"))
        for item in files:
            self.assertGreater(item["bytes"], 0)
            self.assertRegex(item["md5"], re.compile(r"^[0-9a-f]{32}$"))
            self.assertTrue(item["name"].endswith(".feather"))

    def test_downloader_list_mode_is_offline_and_complete(self):
        result = subprocess.run(
            [sys.executable, "scripts/prepare_malecns_data.py", "--list"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        for item in self.payload["files"]:
            self.assertIn(item["name"], result.stdout)
            self.assertIn(item["md5"], result.stdout)

    def test_verifier_rejects_wrong_size_and_accepts_exact_md5(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.feather"
            path.write_bytes(b"MaleCNS")
            ok, detail = prepare_malecns_data.verify(
                path, 7, "01889527b4a4be5dfc9ed7cf55815f35"
            )
            self.assertTrue(ok, detail)
            ok, detail = prepare_malecns_data.verify(
                path, 8, "01889527b4a4be5dfc9ed7cf55815f35"
            )
            self.assertFalse(ok)
            self.assertIn("expected 8", detail)

    def test_downloader_recovers_from_a_complete_corrupt_part(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.feather"
            destination = root / "downloads" / "target.feather"
            part = destination.with_suffix(".feather.part")
            source.write_bytes(b"verified-source")
            part.parent.mkdir(parents=True)
            part.write_bytes(b"x" * len(b"verified-source"))
            digest = prepare_malecns_data.hashlib.md5(
                b"verified-source", usedforsecurity=False
            ).hexdigest()

            prepare_malecns_data.download(
                source.as_uri(), destination, len(b"verified-source"), digest
            )

            self.assertEqual(destination.read_bytes(), b"verified-source")
            self.assertFalse(part.exists())


if __name__ == "__main__":
    unittest.main()
