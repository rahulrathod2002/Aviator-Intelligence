from __future__ import annotations

import asyncio
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import AviatorBackend


async def _main() -> None:
    await AviatorBackend().run()


if __name__ == "__main__":
    asyncio.run(_main())
