"""Layout and generation regression tests for the Rust reg_def backend."""

import dataclasses
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
from src.ti_parser import parse_device


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

    def generate(self, model: Device, *, standalone: bool = False) -> str:
        """Generate twice and check deterministic output."""
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "registers.rs"
            generate_source(path, model, standalone=standalone)
            first = path.read_bytes()
            generate_source(path, model, standalone=standalone)
            self.assertEqual(first, path.read_bytes())
            return first.decode()

    def xml_model(self) -> Device:
        """Load XML with named encodings and descriptions requiring Markdown escaping."""
        return parse_device(pathlib.Path(__file__).parent / "fixtures/device.xml")

    def docs(self, source: str, declaration: str) -> str:
        """Read documentation attached to a declaration, skipping Rust attributes."""
        preceding = source.split(declaration, 1)[0].rstrip().splitlines()
        lines = []
        for original in reversed(preceding):
            line = original.strip()
            if line.startswith("///"):
                lines.append(line.removeprefix("///").strip())
            elif not line.startswith("#["):
                break
        return " ".join(reversed(lines))

    def test_xml_named_values_are_preserved(self) -> None:
        fields = self.xml_model().peripherals[0].registers[0].bitfields
        self.assertEqual(
            [(v.name, v.value) for v in fields[0].named_values], [("UP", 1), ("DOWN", 0)]
        )
        self.assertEqual(fields[0].named_values[1].description, "Count down.")
        self.assertEqual([v.value for v in fields[1].named_values], [0, 2, 8])
        self.assertEqual(fields[2].named_values, ())

    def test_hover_docs_on_getters_and_setters(self) -> None:
        source = self.generate(self.xml_model())
        for declaration in ("pub const fn direction(", "pub fn set_direction("):
            docs = self.docs(source, declaration)
            self.assertIn("Count direction.", docs)
            self.assertIn("Bit 4; XML access: RW; reset: `0x0`", docs)
            self.assertIn("`0x1 (true)` — UP: Count up from zero.", docs)
            self.assertIn("`0x0 (false)` — DOWN: Count down.", docs)
            self.assertIn("local snapshot", docs)
        for declaration in ("pub const fn match_(", "pub fn set_match_("):
            docs = self.docs(source, declaration)
            self.assertIn("Bits 7:5; XML access: RO; reset: `0x2`", docs)
            self.assertIn(r"Match \[7:5\] when x &lt; y; do not dereference \*ptr.", docs)
            self.assertIn("outside field width in XML", docs)
        self.assertIn("XML access: WO", self.docs(source, "pub fn set_clear("))
        self.assertIn("truncated", self.docs(source, "pub fn set_match_("))

    def test_hover_docs_on_registers_and_peripherals(self) -> None:
        source = self.generate(self.xml_model())
        for declaration in (
            "pub mod mode",
            "pub struct Value",
            "pub struct Register",
            "pub mode: mode::Register",
            "pub unsafe fn read(",
            "pub unsafe fn write(",
        ):
            docs = self.docs(source, declaration)
            self.assertIn("Timer mode &amp; control for &lt;channel&gt;.", docs)
            self.assertIn("Register `MODE`; offset `0x4`; width 32 bits.", docs)
        for declaration in ("pub mod test", "pub struct Peripheral", "pub const TEST0:"):
            self.assertIn("Test peripheral.", self.docs(source, declaration))
        self.assertIn("0x40000000", self.docs(source, "pub const TEST0:"))
        self.assertIn("# Safety", self.docs(source, "pub unsafe fn write("))

    def test_wrapping_xml_prose_does_not_create_markdown_lists(self) -> None:
        description = "Configuration. " * 8 + "- First item. + Second item. 1. Third. 2) Fourth."
        source = self.generate(device([Register("DATA", description, 32, 0, [])]))
        self.assertIn(r"\- First item.", source)
        self.assertIn(r"\+ Second item.", source)
        self.assertIn(r"1\. Third.", source)
        self.assertIn(r"2\) Fourth.", source)
        self.assertNotRegex(source, r"(?m)^\s*/// (?:[-+] |\d+[.)] )")

    def test_documentation_does_not_change_generated_operations(self) -> None:
        model = self.xml_model()
        source = self.generate(model)
        plain = device([Register("MODE", "", 32, 4, model.peripherals[0].registers[0].bitfields)])
        # Replace all descriptive metadata, leaving only the layout and accessors.
        plain.peripherals[0].registers[0].bitfields[:] = [
            dataclasses.replace(field, description="", named_values=())
            for field in plain.peripherals[0].registers[0].bitfields
        ]

        def without_docs(text: str) -> str:
            return "\n".join(
                line for line in text.splitlines() if not line.lstrip().startswith("//")
            )

        self.assertEqual(without_docs(source), without_docs(self.generate(plain)))

    def test_standalone_crate_preserves_definitions(self) -> None:
        model = device([Register("DATA", "", 32, 0, [field("ALL", 0, 32)])])
        included = self.generate(model)
        standalone = self.generate(model, standalone=True)
        self.assertNotIn("#![no_std]", included)
        self.assertEqual(standalone.count("#![no_std]"), 1)
        self.assertEqual(standalone.replace("#![no_std]\n", ""), included)
        self.assertLess(standalone.index("#![no_std]"), standalone.index("pub mod"))

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
