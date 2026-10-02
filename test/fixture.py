"""Generate a small register fixture for executable Rust layout tests."""

import pathlib
import sys

from src.device_types import (
    Device,
    PeripheralDefinition,
    PeripheralInstance,
    Register,
    RegisterBitfield,
    RwAccess,
)
from src.rust_generator import generate_source


def field(name: str, offset: int, width: int) -> RegisterBitfield:
    """Construct a read/write field for a fixture."""
    return RegisterBitfield(name, "Fixture field.", offset, width, RwAccess.RW, 0)


def main() -> None:
    """Write the fixture to the command-line output path."""
    registers = [
        Register("BYTE", "", 8, 0, [field("LOW", 0, 3), field("HIGH", 7, 1)]),
        Register("HALF", "", 16, 2, [field("ALL", 0, 16)]),
        Register("WORD", "", 32, 4, [field("MODE", 4, 3), field("TOP", 31, 1)]),
        Register("ALIAS", "", 32, 4, [field("ALL", 0, 32)]),
        Register("DOUBLE", "", 64, 8, [field("ALL", 0, 64)]),
    ]
    model = Device(
        "FIXTURE",
        "CPU",
        [
            PeripheralDefinition(
                "FIXTURE", "", registers, [PeripheralInstance("FIXTURE0", 0, 0x40000000, 16)]
            )
        ],
    )
    generate_source(pathlib.Path(sys.argv[1]), model)


if __name__ == "__main__":
    main()
