"""Decode a Google Drive download into public/private/.

The Drive connector returns a file as JSON ({content: base64, title, ...}).
This writes the bytes under public/private/, which is git-ignored: banners
come from Drive at work time and never enter the repository.

    python3 scripts/drive/save_from_mcp.py <download.json> [subdir]
"""

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / "public" / "private"


def main() -> None:
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    payload = json.loads(Path(sys.argv[1]).read_text())
    target = PRIVATE / (sys.argv[2] if len(sys.argv) == 3 else "")
    target.mkdir(parents=True, exist_ok=True)
    out = target / Path(payload["title"]).name
    out.write_bytes(base64.b64decode(payload["content"]))
    print(out.relative_to(ROOT))


if __name__ == "__main__":
    main()
