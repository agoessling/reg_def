"""Generate layout-only Rust register definitions without MMIO references.

Access permissions and peripheral behavior remain driver responsibilities. A
Register is an address descriptor, not an ownership token. Only volatile access
is unsafe; constructing and manipulating an integer-backed Value is always safe.
"""

import html
import pathlib
import re
import textwrap

from src.device_types import Device, PeripheralDefinition, Register, RegisterBitfield

_KEYWORDS = frozenset(
    "as async await break const continue crate dyn else enum extern false fn for if impl in "
    "let loop match mod move mut pub ref return self Self static struct super trait true "
    "type unsafe use where while abstract become box do final macro override priv typeof "
    "unsized virtual yield try gen".split()
)


def _identifier(name: str) -> str:
    result = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()
    if not result or result[0].isdigit():
        result = "field_" + result
    # A suffix also works for self/Self, which cannot use raw identifiers.
    if result in _KEYWORDS or result in {"bits", "from_bits"}:
        result += "_"
    return result


def _unique(names: list[str], context: str) -> None:
    if len(names) != len(set(names)):
        message = f"Rust identifier collision in {context}: {names}"
        raise ValueError(message)


def _xml_text(description: str) -> str:
    # XML prose is not Markdown: preserve bit ranges, comparisons, and code as literal text.
    escaped = re.sub(r"([\\`*_\[\]#|+\-])", r"\\\1", html.escape(description, quote=False))
    # Wrapping can move an inline list marker to the beginning of a Markdown line.
    return re.sub(r"\b(\d+)([.)])(?=\s)", r"\1\\\2", escaped)


def _doc(description: str, indent: str = "") -> list[str]:
    lines = []
    for paragraph in description.splitlines():
        wrapped = textwrap.wrap(
            paragraph.strip(),
            width=100 - len(indent) - 4,
            break_long_words=False,
            break_on_hyphens=False,
            subsequent_indent="  " if paragraph.startswith("- ") else "",
        )
        lines.extend(indent + "/// " + line for line in wrapped)
        if not wrapped:
            lines.append(indent + "///")
    return lines


def _register_doc(register: Register) -> str:
    return (
        f"{_xml_text(register.description)}\n\n"
        f"Register `{register.name}`; offset `{register.address_offset:#x}`; "
        f"width {register.bit_width} bits."
    ).strip()


def _field_doc(field: RegisterBitfield) -> str:
    location = (
        f"Bit {field.bit_offset}"
        if field.bit_width == 1
        else f"Bits {field.bit_offset + field.bit_width - 1}:{field.bit_offset}"
    )
    result = (
        f"{_xml_text(field.description)}\n\n"
        f"{location}; XML access: {field.rw_access.name}; reset: `{field.reset_value:#x}`."
    ).strip()
    if field.named_values:
        result += "\n\nXML values:\n"
        for value in field.named_values:
            encoding = f"{value.value:#x}"
            if field.bit_width == 1 and value.value in (0, 1):
                encoding += " (true)" if value.value else " (false)"
            # Some vendor XML values exceed their field width; retain and flag rather than infer.
            note = ""
            if not 0 <= value.value < (1 << field.bit_width):
                note = " (outside field width in XML)"
            result += (
                f"- `{encoding}` — {_xml_text(value.name)}: "
                f"{_xml_text(value.description)}{note}\n"
            )
    return result.rstrip()


def _register(register: Register) -> list[str]:
    name = _identifier(register.name)
    integer = f"u{register.bit_width}"
    fields = [_identifier(field.name) for field in register.bitfields]
    _unique(fields + ["set_" + field for field in fields], register.name)
    documentation = _register_doc(register)
    result = _doc(documentation)
    result += [
        f"pub mod {name} {{",
        f"    pub const OFFSET: usize = {register.address_offset:#x};",
        *_doc(
            documentation + "\n\nLocal snapshot; field operations do not access hardware.", "    "
        ),
        "    #[repr(transparent)]",
        "    #[derive(Clone, Copy, Debug, Eq, PartialEq)]",
        f"    pub struct Value({integer});",
        "    impl Value {",
        "        #[inline(always)]",
        f"        pub const fn from_bits(bits: {integer}) -> Self {{ Self(bits) }}",
        "        #[inline(always)]",
        f"        pub const fn bits(self) -> {integer} {{ self.0 }}",
    ]
    for field, field_name in zip(register.bitfields, fields, strict=True):
        if field.bit_width == 0:
            message = f"Zero-width field: {register.name}.{field.name}"
            raise ValueError(message)
        mask = (1 << field.bit_width) - 1
        shifted_mask = mask << field.bit_offset
        field_type = "bool" if field.bit_width == 1 else integer
        full_width = field.bit_width == register.bit_width and field.bit_offset == 0
        expression = "self.0" if full_width else f"((self.0 >> {field.bit_offset}) & {mask:#x})"
        assignment = (
            "self.0 = value;"
            if full_width
            else f"self.0 = (self.0 & !{shifted_mask:#x})"
            f" | (((value as {integer}) & {mask:#x}) << {field.bit_offset});"
        )
        if field.bit_width == 1:
            expression += " != 0"
        result += _doc(
            _field_doc(field) + "\n\nRead this field from the local snapshot.", "        "
        )
        result += [
            "        #[inline(always)]",
            f"        pub const fn {field_name}(self) -> {field_type} {{ {expression} }}",
            *_doc(
                _field_doc(field)
                + "\n\nSet this field in the local snapshot, preserving other bits."
                + ("" if field.bit_width == 1 else " Excess high bits are truncated."),
                "        ",
            ),
            "        #[inline(always)]",
            f"        pub fn set_{field_name}(&mut self, value: {field_type}) {{",
            f"            {assignment}",
            "        }",
        ]
    result += [
        "    }",
        f"    impl From<{integer}> for Value {{",
        "        /// Wrap raw bits without validating hardware-specific encodings.",
        "        #[inline(always)]",
        f"        fn from(bits: {integer}) -> Self {{ Self::from_bits(bits) }}",
        "    }",
        *_doc(
            documentation + "\n\nRaw address descriptor; does not confer peripheral ownership.",
            "    ",
        ),
        "    #[derive(Clone, Copy)]",
        "    pub struct Register { address: usize }",
        "    impl Register {",
        "        pub const fn at(address: usize) -> Self { Self { address } }",
        "        pub const fn address(self) -> usize { self.address }",
        *_doc(documentation + "\n\nRead hardware into a local snapshot.\n", "        "),
        "        /// # Safety",
        "        /// Caller must ensure a valid aligned register address, enabled clocks,",
        "        /// permitted access and side effects, and appropriate synchronization.",
        "        #[inline(always)]",
        "        pub unsafe fn read(self) -> Value {",
        "            // SAFETY: The caller supplies the MMIO access guarantees above.",
        "            Value(unsafe { core::ptr::read_volatile(self.address as "
        f"*const {integer}) }})",
        "        }",
        *_doc(documentation + "\n\nWrite the local snapshot to hardware.\n", "        "),
        "        /// # Safety",
        "        /// Caller must ensure a valid aligned register address, enabled clocks,",
        "        /// permitted access/value and side effects, and appropriate synchronization.",
        "        #[inline(always)]",
        "        pub unsafe fn write(self, value: Value) {",
        "            // SAFETY: The caller supplies the MMIO access guarantees above.",
        "            unsafe { core::ptr::write_volatile(self.address as "
        f"*mut {integer}, value.0) }}",
        "        }",
        "    }",
        "}",
    ]
    return result


def _peripheral(peripheral: PeripheralDefinition) -> list[str]:
    name = _identifier(peripheral.name)
    _unique([_identifier(r.name) for r in peripheral.registers], peripheral.name)
    result = _doc(_xml_text(peripheral.description))
    result += [
        "#[allow(dead_code, unused_parens, clippy::identity_op, clippy::unnecessary_cast)]",
        f"pub mod {name} {{",
    ]
    for register in peripheral.registers:
        result.extend("    " + line for line in _register(register))
    result += [
        *_doc(
            _xml_text(peripheral.description)
            + "\n\nRegister addresses for one peripheral; this is not an ownership token.",
            "    ",
        ),
        "    #[derive(Clone, Copy)]",
        "    pub struct Peripheral {",
    ]
    for register in peripheral.registers:
        reg_name = _identifier(register.name)
        result.extend(_doc(_register_doc(register), "        "))
        result.append(f"        pub {reg_name}: {reg_name}::Register,")
    result += [
        "    }",
        "    impl Peripheral {",
        "        pub const fn at(base: usize) -> Self {",
        "            Self {",
    ]
    for register in peripheral.registers:
        reg_name = _identifier(register.name)
        result.append(
            f"                {reg_name}: {reg_name}::Register::at(base + {reg_name}::OFFSET),"
        )
    result += ["            }", "        }", "    }", "}"]
    for instance in peripheral.instances:
        if instance.address % max((r.bit_width // 8 for r in peripheral.registers), default=1):
            message = f"Unaligned peripheral instance: {instance.name}"
            raise ValueError(message)
        result += [
            *_doc(
                _xml_text(peripheral.description) + f"\n\nBase address: `{instance.address:#x}`."
            ),
            "#[allow(dead_code)]",
            f"pub const {_identifier(instance.name).upper()}: {name}::Peripheral =",
            f"    {name}::Peripheral::at({instance.address:#x});",
        ]
    return result


def generate_source(path: pathlib.Path, device: Device, *, standalone: bool = False) -> None:
    """Write deterministic Rust definitions from the shared device model."""
    _unique([_identifier(p.name) for p in device.peripherals], device.part_number)
    _unique(
        [_identifier(i.name).upper() for p in device.peripherals for i in p.instances],
        device.part_number,
    )
    lines = [
        "// Generated by reg_def; do not edit.",
        "// Register layout only. Hardware behavior and ownership belong to drivers.",
    ]
    if standalone:
        lines.append("#![no_std]")
    for peripheral in device.peripherals:
        lines.extend(_peripheral(peripheral))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
