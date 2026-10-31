"""Download, verify, and rebuild the portable MaleCNS evidence.

The downloader uses only Python's standard library. PyArrow is required by the
subsequent extraction scripts and is declared in requirements-data.txt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "malecns" / "raw-files.json"


def load_manifest(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {"dataset", "base_url", "destination", "files"}
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"Manifest is missing: {', '.join(sorted(missing))}")
    return payload


def md5sum(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, expected_bytes: int, expected_md5: str) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        return False, f"size {actual_bytes:,}, expected {expected_bytes:,}"
    actual_md5 = md5sum(path)
    if actual_md5.lower() != expected_md5.lower():
        return False, f"MD5 {actual_md5}, expected {expected_md5}"
    return True, "verified"


def download(url: str, destination: Path, expected_bytes: int, expected_md5: str) -> None:
    ok, _ = verify(destination, expected_bytes, expected_md5)
    if ok:
        print(f"Verified {destination.name}")
        return

    part = destination.with_suffix(destination.suffix + ".part")
    if destination.exists() and destination.stat().st_size < expected_bytes and not part.exists():
        destination.replace(part)
    elif destination.exists():
        destination.unlink()

    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 9):
        if part.exists() and part.stat().st_size >= expected_bytes:
            part_ok, _ = verify(part, expected_bytes, expected_md5)
            if part_ok:
                os.replace(part, destination)
                print(f"Verified {destination.name}")
                return
            part.unlink()
        offset = part.stat().st_size if part.exists() else 0
        headers = {"User-Agent": "CHRONOS-MaleCNS-reproducer/1.0"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        try:
            print(f"Downloading {destination.name} from byte {offset:,} (attempt {attempt}/8)")
            request = Request(url, headers=headers)
            with urlopen(request, timeout=120) as response:
                resumed = offset > 0 and getattr(response, "status", 200) == 206
                mode = "ab" if resumed else "wb"
                with part.open(mode) as output:
                    while True:
                        chunk = response.read(8 * 1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
            if not part.exists() or part.stat().st_size != expected_bytes:
                actual_bytes = part.stat().st_size if part.exists() else 0
                raise IOError(
                    f"downloaded {actual_bytes:,} bytes, expected {expected_bytes:,}"
                )
            if md5sum(part).lower() != expected_md5.lower():
                raise IOError("downloaded file failed MD5 verification")
            os.replace(part, destination)
            print(f"Verified {destination.name}")
            return
        except (HTTPError, URLError, OSError, TimeoutError) as exc:
            if attempt == 8:
                raise RuntimeError(f"Download failed for {destination.name}: {exc}") from exc
            print(f"Retrying after error: {exc}", file=sys.stderr)
            time.sleep(min(5 * attempt, 30))


def run_pipeline() -> None:
    commands = [
        [sys.executable, "scripts/extract_verified_odor_motor_path.py"],
        [sys.executable, "scripts/export_portable_runtime.py"],
        [sys.executable, "scripts/enrich_verified_pathway_synapses.py"],
        [sys.executable, "scripts/validate_verified_pathway.py"],
    ]
    for command in commands:
        print(f"Running {' '.join(command)}")
        subprocess.run(command, cwd=ROOT, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="List inputs without downloading")
    group.add_argument("--verify-only", action="store_true", help="Verify local inputs without downloading")
    group.add_argument("--build-only", action="store_true", help="Skip download and run the rebuild pipeline")
    group.add_argument("--download-only", action="store_true", help="Download and verify, but do not rebuild")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_manifest(args.manifest.resolve())
    data_dir = (ROOT / manifest["destination"]).resolve()
    files = manifest["files"]

    if args.list:
        print(f"{manifest['dataset']} -> {data_dir}")
        for item in files:
            url = f"{manifest['base_url'].rstrip('/')}/{item['name']}"
            print(f"{item['name']}\t{item['bytes']}\t{item['md5']}\t{url}")
        return 0

    if args.verify_only:
        failures = 0
        for item in files:
            ok, detail = verify(data_dir / item["name"], item["bytes"], item["md5"])
            print(f"{'OK' if ok else 'FAIL'} {item['name']}: {detail}")
            failures += not ok
        return 1 if failures else 0

    if not args.build_only:
        for item in files:
            download(
                f"{manifest['base_url'].rstrip('/')}/{item['name']}",
                data_dir / item["name"],
                item["bytes"],
                item["md5"],
            )

    if not args.download_only:
        run_pipeline()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
