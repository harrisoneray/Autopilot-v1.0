"""Compatibility launcher; prefer python -m usv."""
from usv.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
