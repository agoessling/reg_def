"""Layout and generation regression tests for the Rust reg_def backend."""

import pathlib
import tempfile
import unittest

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
    return RegisterBitfield(name, "A field.", offset, width, RwAccess.RW, 0)


def device(registers: list[Register]) -> Device:
    """Wrap fixture registers in one fixed-address peripheral."""
    return Device(
        "TEST",
        "CPU",
        [
            PeripheralDefinition(
                "TEST",
                "Test peripheral.",
                registers,
                [PeripheralInstance("TEST0", 0, 0x40000000, 64)],
            )
        ],
    )


class GeneratorTest(unittest.TestCase):
    """Exercise Rust source generation without accessing hardware."""

    def generate(self, model: Device) -> str:
        """Generate twice and check deterministic output."""
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "registers.rs"
            generate_source(path, model)
            first = path.read_bytes()
            generate_source(path, model)
            self.assertEqual(first, path.read_bytes())
            return first.decode()

    def test_widths_and_full_width_masks(self) -> None:
        for width in (8, 16, 32, 64):
            source = self.generate(
                device([Register("DATA", "", width, 0, [field("ALL", 0, width)])])
            )
            self.assertIn(f"pub struct Value(u{width})", source)
            self.assertIn(f"as *const u{width}", source)
            self.assertIn(f"as *mut u{width}", source)
            self.assertIn("self.0 = value;", source)
            self.assertIn(f"pub const fn all(self) -> u{width} {{ self.0 }}", source)

    def test_aliases_and_keyword_fields(self) -> None:
        source = self.generate(
            device(
                [
                    Register("READ", "", 32, 4, [field("MATCH", 31, 1)]),
                    Register("WRITE", "", 32, 4, [field("TYPE", 0, 4)]),
                ]
            )
        )
        self.assertEqual(source.count("pub const OFFSET: usize = 0x4;"), 2)
        self.assertIn("pub const fn match_(self) -> bool", source)
        self.assertIn("pub fn set_type_", source)
        self.assertIn("pub const TEST0:", source)

    def test_noncontiguous_fields_preserve_other_bits(self) -> None:
        source = self.generate(device([Register("CFG", "", 32, 0, [field("MODE", 4, 3)])]))
        self.assertIn("self.0 & !0x70", source)
        self.assertIn("& 0x7) << 4", source)

    def test_identifier_collision_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "identifier collision"):
            self.generate(
                device([Register("CFG", "", 32, 0, [field("MODE", 0, 1), field("mode", 1, 1)])])
            )

    def test_zero_width_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.generate(device([Register("CFG", "", 32, 0, [field("EMPTY", 0, 0)])]))


if __name__ == "__main__":
    unittest.main()
