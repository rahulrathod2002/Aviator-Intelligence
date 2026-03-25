import asyncio

from src.pipeline.runner import CaptureRunner


def main() -> None:
    asyncio.run(CaptureRunner().run())


if __name__ == "__main__":
    main()
