from __future__ import annotations

import sys
from pathlib import Path


def _main() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from aws_ai_energy.generate.seismic_catalog import main

    main()


if __name__ == "__main__":
    _main()
