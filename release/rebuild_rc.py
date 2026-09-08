from __future__ import annotations

import base64
import bz2
import hashlib
from pathlib import Path

PARTS = tuple(f"part-{index:02d}.b64" for index in range(1, 12))
COMPRESSED_SHA256 = "1f744e1af5e12bbfca1bd3f4c735fd136f5bdaa7557af85140ced15b365dddeb"
PATCH_SHA256 = "f0d4216ab6dacda8e564d4e6add481dfa2907aff2ce2dbab1d26b77623cfff95"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    here = Path(__file__).resolve().parent
    parts_dir = here / "rc-patch"
    encoded = "".join((parts_dir / name).read_text(encoding="ascii") for name in PARTS)
    compressed = base64.b64decode(encoded, validate=True)
    actual_compressed = sha256(compressed)
    if actual_compressed != COMPRESSED_SHA256:
        raise SystemExit(
            f"compressed patch SHA-256 mismatch: {actual_compressed} != {COMPRESSED_SHA256}"
        )
    patch = bz2.decompress(compressed)
    actual_patch = sha256(patch)
    if actual_patch != PATCH_SHA256:
        raise SystemExit(f"patch SHA-256 mismatch: {actual_patch} != {PATCH_SHA256}")
    output = here / "kairos-rc.git.patch"
    output.write_bytes(patch)
    print(f"wrote {output}")
    print(f"patch_sha256={actual_patch}")
    print("Apply this patch only to the canonical base identified in RC_MANIFEST.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
