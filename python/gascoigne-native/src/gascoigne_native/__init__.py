"""Data package: the bundled libgascoigne for every platform (see spec/native.md).

The SDK reads `LIB_DIR`; this package has no code of its own.
"""

from pathlib import Path

LIB_DIR = Path(__file__).parent / "lib"
