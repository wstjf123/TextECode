from __future__ import annotations

import shutil
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python vendor_native.py <directory-containing-native-files>")

    source_dir = Path(sys.argv[1]).resolve()
    if not source_dir.is_dir():
        raise FileNotFoundError(source_dir)

    package_dir = Path(__file__).resolve().parents[1] / "src" / "textecode" / "bin" / "win-x64"
    package_dir.mkdir(parents=True, exist_ok=True)

    stale_pdb = package_dir / "TextECode.NativeBridge.pdb"
    if stale_pdb.exists():
        stale_pdb.unlink()

    required = ["TextECode.NativeBridge.dll"]

    for name in required:
        source = source_dir / name
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, package_dir / name)

    print(package_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
