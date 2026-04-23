"""Allow running as `python -m ssidctl`."""

import sys

from ssidctl.cli import main

if __name__ == "__main__":
    sys.exit(main())
