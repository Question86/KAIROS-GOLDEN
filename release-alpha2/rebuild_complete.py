from __future__ import annotations

import base64
import bz2
import hashlib
from pathlib import Path

FILES = tuple(f"complete/part-{i:02d}.b64" for i in range(7))
COMPRESSED_SHA256 = "a995c62731d751f8c7190d5096d17c9df9d14824ca3ad24f546ad8c609cd93eb"
PATCH_SHA256 = "f2454f25435e068d92469545142c93a781efb041064516e28b489a9a41f59e4d"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    here = Path(__file__).resolve().parent
    encoded = "".join((here / name).read_text(encoding="ascii") for name in FILES)
    compressed = base64.b64decode(encoded, validate=True)
    actual_compressed = sha256(compressed)
    if actual_compressed != COMPRESSED_SHA256:
        raise SystemExit(f"compressed alpha.2 patch hash mismatch: {actual_compressed}")
    patch = bz2.decompress(compressed)
    actual_patch = sha256(patch)
    if actual_patch != PATCH_SHA256:
        raise SystemExit(f"alpha.2 patch hash mismatch: {actual_patch}")
    output = here / "KAIROS-alpha2-source-complete.patch"
    output.write_bytes(patch)
    print(f"patch={output}")
    print(f"sha256={actual_patch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
