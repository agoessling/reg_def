from collections import defaultdict
import pathlib
import textwrap

from device_types import Device, PeripheralDefinition, Register


def type_from_bits(bit_width: int) -> str:
    if bit_width <= 8:
        return "uint8_t"
    if bit_width <= 16:
        return "uint16_t"
    if bit_width <= 32:
        return "uint32_t"
    if bit_width <= 64:
        return "uint64_t"
    raise ValueError(f"Bit width ({bit_width}) too large.")


def type_from_bytes(bytes: int) -> str:
    if bytes <= 1:
        return "uint8_t"
    if bytes <= 2:
        return "uint16_t"
    if bytes <= 4:
        return "uint32_t"
    if bytes <= 8:
        return "uint64_t"
    raise ValueError(f"Bytes ({bytes}) too large.")


def bytes_from_bits(bit_width: int) -> int:
    if bit_width == 8:
        return 1
    if bit_width == 16:
        return 2
    if bit_width == 32:
        return 4
    if bit_width == 64:
        return 8
    raise ValueError(f"Incompatible bits ({bit_width}) for bytes.")


def capitalize_sentence(text: str) -> str:
    return text[0:1].upper() + text[1:]


def wrap_comment(text: str, indent: str = "", width: int = 100) -> str:
    indent = indent + "// "
    return textwrap.fill(
        capitalize_sentence(text), width=width, initial_indent=indent, subsequent_indent=indent
    )


def get_header_header(device: Device) -> str:
    return f"""\
#pragma once

#include <assert.h>
#include <stddef.h>
#include <stdint.h>

// {device.part_number} register definitions.
// CPU: {device.cpu_name}"""


def get_bitfield_definition(register: Register) -> str:
    bitfield_listings = []
    data_type = type_from_bits(register.bit_width)

    offset = 0
    unused_counter = 0
    for bitfield in register.bitfields:
        if bitfield.bit_offset > offset:
            unused_size = bitfield.bit_offset - offset
            bitfield_listings.append(
                f"  {data_type} unused{unused_counter} : {unused_size};  // Unused field."
            )
            unused_counter += 1

        bitfield_listings.append(wrap_comment(bitfield.description, " " * 2, 98))
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


def get_register_typedef(peripheral: PeripheralDefinition, register: Register) -> str:
    return f"{peripheral.name.capitalize()}{register.name.capitalize()}RegDef"


def get_register_definition(peripheral: PeripheralDefinition, register: Register) -> str:
    data_type = type_from_bits(register.bit_width)
    data_bytes = bytes_from_bits(register.bit_width)
    typedef_name = get_register_typedef(peripheral, register)

    s = f"""\
// {peripheral.name.upper()} {register.name.upper()} register definition.
{wrap_comment(peripheral.description)}
typedef union {{
{textwrap.indent(get_bitfield_definition(register), '  ')}
  {data_type} raw;  // Entire register as raw {data_type}.
}} {typedef_name};

static_assert(sizeof({typedef_name}) == {data_bytes});"""

    return s


def get_peripheral_typedef(peripheral: PeripheralDefinition) -> str:
    return f"{peripheral.name.capitalize()}PeriphDef"


def get_peripheral_struct(peripheral: PeripheralDefinition) -> str:
    peripheral_typedef = get_peripheral_typedef(peripheral)

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
            fields.append(wrap_comment(reg_list[0].description, " " * 2))
            fields.append(
                f"  {get_register_typedef(peripheral, reg_list[0])} {reg_list[0].name.upper()};"
            )
            asserts.append(
                f"static_assert(offsetof({peripheral_typedef}, {reg_list[0].name.upper()})"
                f" == {reg_list[0].address_offset});"
            )
        # For registers which overlap, create anonymouse union.
        else:
            union_fields = []
            for register in reg_list:
                union_fields.append(wrap_comment(register.description, " " * 4))
                union_fields.append(
                    f"    {get_register_typedef(peripheral, register)} {register.name.upper()};"
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

        offset = reg_offset + bytes_from_bits(reg_list[0].bit_width)

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


def get_peripheral_definition(peripheral: PeripheralDefinition) -> str:
    register_listing = "\n\n".join(
        get_register_definition(peripheral, r) for r in peripheral.registers
    )

    return f"""\
// {peripheral.name} registers.

{register_listing}

{get_peripheral_struct(peripheral)}"""


def get_peripheral_instances(peripheral: PeripheralDefinition) -> str:
    define_block = "\n".join(
        f"#define {inst.name.upper()} (*((volatile {get_peripheral_typedef(peripheral)}*){inst.address:#010x}))"
        for inst in peripheral.instances
    )
    return f"""\
{define_block}"""


def generate_header(path: pathlib.Path, device: Device) -> None:
    with path.open("w") as f:
        f.write(get_header_header(device))
        f.write("\n\n")

        peripheral_definitions = [get_peripheral_definition(p) for p in device.peripherals]
        f.write("\n\n".join(peripheral_definitions))

        f.write("\n\n")

        instances = [get_peripheral_instances(p) for p in device.peripherals]
        f.write("\n\n".join(instances))
