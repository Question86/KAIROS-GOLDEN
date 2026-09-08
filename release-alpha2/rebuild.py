from __future__ import annotations

import base64
import bz2
import hashlib
from pathlib import Path

PARTS = tuple(f"part-{i:02d}.b64" for i in range(7))
COMPRESSED_SHA256 = "357272c18075816205a987af8f6fab7e2db20662fcdc1d09dc885836912af904"
PATCH_SHA256 = "8d97f550be38ddf4837b09fd969de2d99aa3886a3088bb6ad59b7304c900bc2f"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    here = Path(__file__).resolve().parent
    encoded = "".join((here / "patch" / name).read_text(encoding="ascii") for name in PARTS)
    compressed = base64.b64decode(encoded, validate=True)
    if sha256(compressed) != COMPRESSED_SHA256:
        raise SystemExit("compressed alpha.2 patch hash mismatch")
    patch = bz2.decompress(compressed)
    if sha256(patch) != PATCH_SHA256:
        raise SystemExit("alpha.2 patch hash mismatch")
    output = here / "KAIROS-alpha2-source.patch"
    output.write_bytes(patch)
    print(f"patch={output}")
    print(f"sha256={sha256(patch)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
