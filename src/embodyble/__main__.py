"""Default execution entry point if running the package via python -m."""
import asyncio
import sys

from . import cli


def main():
    """Run cli from script entry point."""
    asyncio.run(cli.main())


if __name__ == "__main__":
    sys.exit(main())
