"""Generate C header from device definition."""

import pathlib
import re
import textwrap
from collections import defaultdict

from src.device_types import Device, PeripheralDefinition, Register


def _type_from_bits(bit_width: int) -> str:
    if bit_width <= 8:
        return "uint8_t"
    if bit_width <= 16:
        return "uint16_t"
    if bit_width <= 32:
        return "uint32_t"
    if bit_width <= 64:
        return "uint64_t"
    msg = f"Bit width ({bit_width}) too large."
    raise ValueError(msg)


def _bytes_from_bits(bit_width: int) -> int:
    if bit_width == 8:
        return 1
    if bit_width == 16:
        return 2
    if bit_width == 32:
        return 4
    if bit_width == 64:
        return 8
    msg = f"Incompatible bits ({bit_width}) for bytes."
    raise ValueError(msg)


def _to_camel_case(text: str) -> str:
    orig_words = re.split("[_ ]", text)

    output_words = []
    for word in orig_words:
        if word.isupper():
            output_words.append(word[:1].upper() + word[1:].lower())
            continue
        output_words.append(word[:1].upper() + word[1:])

    return "".join(output_words)


def _capitalize_sentence(text: str) -> str:
    return text[0:1].upper() + text[1:]


def _wrap_comment(text: str, indent: str = "", width: int = 100) -> str:
    indent = indent + "// "
    return textwrap.fill(
        _capitalize_sentence(text), width=width, initial_indent=indent, subsequent_indent=indent
    )


def _get_header_header(device: Device) -> str:
    return f"""\
#pragma once

#include <assert.h>
#include <stddef.h>
#include <stdint.h>

// {device.part_number} register definitions.
// CPU: {device.cpu_name}"""


def _get_bitfield_definition(register: Register) -> str:
    bitfield_listings = []
    data_type = _type_from_bits(register.bit_width)

    offset = 0
    unused_counter = 0
    for bitfield in register.bitfields:
        if bitfield.bit_offset > offset:
            unused_size = bitfield.bit_offset - offset
            bitfield_listings.append(
                f"  {data_type} unused{unused_counter} : {unused_size};  // Unused field."
            )
            unused_counter += 1

        bitfield_listings.append(_wrap_comment(bitfield.description, " " * 2, 98))
        bitfield_listings.append(f"  {data_type} {bitfield.name.upper()} : {bitfield.bit_width};")

        offset = bitfield.bit_offset + bitfield.bit_width

    if offset < register.bit_width:
        unused_size = register.bit_width - offset
        bitfield_listings.append(
            f"  {data_type} unused{unused_counter} : {unused_size};  // Unused field."
        )

    bitfield_block = "\n".join(bitfield_listings)

    return f"""\
struct {{
{bitfield_block}
}};"""


def _get_register_typedef(peripheral: PeripheralDefinition, register: Register) -> str:
    return f"{_to_camel_case(peripheral.name)}{_to_camel_case(register.name)}RegDef"


def _get_register_definition(peripheral: PeripheralDefinition, register: Register) -> str:
    data_type = _type_from_bits(register.bit_width)
    data_bytes = _bytes_from_bits(register.bit_width)
    typedef_name = _get_register_typedef(peripheral, register)

    return f"""\
// {peripheral.name.upper()} {register.name.upper()} register definition.
{_wrap_comment(peripheral.description)}
typedef union {{
{textwrap.indent(_get_bitfield_definition(register), '  ')}
  {data_type} raw;  // Entire register as raw {data_type}.
}} {typedef_name};

static_assert(sizeof({typedef_name}) == {data_bytes});"""


def _get_peripheral_typedef(peripheral: PeripheralDefinition) -> str:
    return f"{_to_camel_case(peripheral.name)}PeriphDef"


def _get_peripheral_struct(peripheral: PeripheralDefinition) -> str:
    peripheral_typedef = _get_peripheral_typedef(peripheral)

    fields = []
    asserts = []

    if peripheral.instances:
        asserts.append(
            f"static_assert(sizeof({peripheral_typedef}) == {peripheral.instances[0].size});"
        )

    # Collect registers by offset.
    registers = defaultdict(list)
    for register in peripheral.registers:
        registers[register.address_offset].append(register)

    offset = 0
    unused_counter = 0
    for reg_offset, reg_list in registers.items():
        if reg_offset > offset:
            unused_size = reg_offset - offset
            fields.append(
                f"  uint8_t unused{unused_counter}[{unused_size}];  // Unused address space."
            )
            unused_counter += 1

        if len(reg_list) == 1:
            fields.append(_wrap_comment(reg_list[0].description, " " * 2))
            fields.append(
                f"  {_get_register_typedef(peripheral, reg_list[0])} {reg_list[0].name.upper()};"
            )
            asserts.append(
                f"static_assert(offsetof({peripheral_typedef}, {reg_list[0].name.upper()})"
                f" == {reg_list[0].address_offset});"
            )
        # For registers which overlap, create anonymouse union.
        else:
            union_fields = []
            for register in reg_list:
                union_fields.append(_wrap_comment(register.description, " " * 4))
                union_fields.append(
                    f"    {_get_register_typedef(peripheral, register)} {register.name.upper()};"
                )
                asserts.append(
                    f"static_assert(offsetof({peripheral_typedef}, {register.name.upper()})"
                    f" == {register.address_offset});"
                )

            union_block = "\n".join(union_fields)

            fields.append(f"""\
  union {{
{union_block}
  }};""")

        offset = reg_offset + _bytes_from_bits(reg_list[0].bit_width)

    if peripheral.instances and offset < peripheral.instances[0].size:
        unused_size = peripheral.instances[0].size - offset
        fields.append(f"  uint8_t unused{unused_counter}[{unused_size}];  // Unused address space.")

    field_block = "\n".join(fields)
    assert_block = "\n".join(asserts)

    return f"""\
typedef struct {{
{field_block}
}} {peripheral_typedef};

{assert_block}"""


def _get_peripheral_definition(peripheral: PeripheralDefinition) -> str:
    register_listing = "\n\n".join(
        _get_register_definition(peripheral, r) for r in peripheral.registers
    )

    return f"""\
// {peripheral.name} registers.

{register_listing}

{_wrap_comment(peripheral.description)}
{_get_peripheral_struct(peripheral)}"""


def _get_peripheral_instances(peripheral: PeripheralDefinition) -> str:
    instance_defs = "\n".join(
        f"{_wrap_comment(peripheral.description)}\n"
        f"static volatile {_get_peripheral_typedef(peripheral)} *const {inst.name.upper()} "
        f"= (volatile {_get_peripheral_typedef(peripheral)} *){inst.address:#010x};"
        for inst in peripheral.instances
    )

    array_def = ""
    if len(peripheral.instances) > 1 and all(
        inst.index is not None for inst in peripheral.instances
    ):
        array_elems = []
        for instance in peripheral.instances:
            while len(array_elems) < instance.index:  # pyright: ignore[reportOperatorIssue]
                array_elems.append("NULL")
            array_elems.append(instance.name.upper())
        elems_string = ",\n".join(array_elems)
        array_def = (
            f"\n\n{_wrap_comment(peripheral.description)}\n"
            f"static volatile {_get_peripheral_typedef(peripheral)} *const "
            f"{peripheral.name.upper()}[{len(peripheral.instances)}] = {{\n"
            f"{textwrap.indent(elems_string, ' ' * 4)},\n}};"
        )

    return instance_defs + array_def


def generate_header(path: pathlib.Path, device: Device) -> None:
    """Write C header to file from device definition."""
    with path.open("w") as f:
        f.write(_get_header_header(device))
        f.write("\n\n")

        peripheral_definitions = [_get_peripheral_definition(p) for p in device.peripherals]
        f.write("\n\n".join(peripheral_definitions))

        f.write("\n\n")

        f.write("// Peripheral instance definitions.\n\n")
        instances = [_get_peripheral_instances(p) for p in device.peripherals]
        f.write("\n\n".join(instances))
