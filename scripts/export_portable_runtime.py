"""Export the small runtime cache used by a normal CHRONOS checkout.

Run this only on a machine that already has the official MaleCNS annotation and
connectome-weight Feather files. The result contains the selected odor and
compass summaries, not the full connectome.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import server


def main() -> None:
    if not server.TYPES.exists() or not server.CONNECTIONS.exists():
        raise SystemExit("Official annotation and connectome-weight tables are required")
    output = Path(server.PORTABLE_CIRCUITS)
    payload = server.circuits()
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
