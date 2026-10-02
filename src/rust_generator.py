"""Generate layout-only Rust register definitions without MMIO references.

Access permissions and peripheral behavior remain driver responsibilities. A
Register is an address descriptor, not an ownership token. Only volatile access
is unsafe; constructing and manipulating an integer-backed Value is always safe.
"""

import pathlib
import re

from src.device_types import Device, PeripheralDefinition, Register

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


def _comment(description: str, indent: str = "") -> list[str]:
    return [indent + "// " + line for line in description.splitlines()]


def _register(register: Register) -> list[str]:
    name = _identifier(register.name)
    integer = f"u{register.bit_width}"
    fields = [_identifier(field.name) for field in register.bitfields]
    _unique(fields + ["set_" + field for field in fields], register.name)
    result = _comment(register.description)
    result += [
        f"pub mod {name} {{",
        f"    pub const OFFSET: usize = {register.address_offset:#x};",
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
        result += _comment(field.description, "        ")
        result += [
            "        #[inline(always)]",
            f"        pub const fn {field_name}(self) -> {field_type} {{ {expression} }}",
            "        /// Set this field, truncating excess high bits and preserving other bits.",
            "        #[inline(always)]",
            f"        pub fn set_{field_name}(&mut self, value: {field_type}) {{",
            f"            {assignment}",
            "        }",
        ]
    result += [
        "    }",
        "    /// Raw address descriptor; does not confer peripheral ownership.",
        "    #[derive(Clone, Copy)]",
        "    pub struct Register { address: usize }",
        "    impl Register {",
        "        pub const fn at(address: usize) -> Self { Self { address } }",
        "        pub const fn address(self) -> usize { self.address }",
        "        /// # Safety",
        "        /// Caller must ensure a valid aligned register address, enabled clocks,",
        "        /// permitted access and side effects, and appropriate synchronization.",
        "        #[inline(always)]",
        "        pub unsafe fn read(self) -> Value {",
        "            // SAFETY: The caller supplies the MMIO access guarantees above.",
        "            Value(unsafe { core::ptr::read_volatile(self.address as "
        f"*const {integer}) }})",
        "        }",
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
    result = _comment(peripheral.description)
    result += [
        "#[allow(dead_code, unused_parens, clippy::identity_op, clippy::unnecessary_cast)]",
        f"pub mod {name} {{",
    ]
    for register in peripheral.registers:
        result.extend("    " + line for line in _register(register))
    result += [
        "    /// Register addresses for one peripheral; this is not an ownership token.",
        "    #[derive(Clone, Copy)]",
        "    pub struct Peripheral {",
    ]
    for register in peripheral.registers:
        reg_name = _identifier(register.name)
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
            "#[allow(dead_code)]",
            f"pub const {_identifier(instance.name).upper()}: {name}::Peripheral =",
            f"    {name}::Peripheral::at({instance.address:#x});",
        ]
    return result


def generate_source(path: pathlib.Path, device: Device) -> None:
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
    for peripheral in device.peripherals:
        lines.extend(_peripheral(peripheral))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
