from __future__ import annotations

import subprocess
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils.config import config


def main() -> None:
    output_path = ROOT.parent / "aviator.png"
    command = ["adb"]
    if config.device_id:
        command += ["-s", config.device_id]
    command += ["exec-out", "screencap", "-p"]

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="ignore") or "adb screencap failed")

    output_path.write_bytes(result.stdout)
    print(f"saved {output_path}")


if __name__ == "__main__":
    main()
