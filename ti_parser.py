"""Parse TI XML device description format."""

import pathlib
import xml.etree.ElementTree as et
from collections import defaultdict

from device_types import (
    Device,
    PeripheralDefinition,
    PeripheralInstance,
    Register,
    RegisterBitfield,
    RwAccess,
)


def _get_attr(element: et.Element, attr: str) -> str:
    val = element.get(attr)
    if val is None:
        msg = f'No attribute "{attr}" in {element.tag}'
        raise KeyError(msg)
    return val


def _parse_register_bitfield(elem: et.Element) -> RegisterBitfield:
    rw_access_mapping = {
        "R": RwAccess.RO,
        "RO": RwAccess.RO,
        "W": RwAccess.WO,
        "WO": RwAccess.WO,
        "": RwAccess.RW,
        "RW": RwAccess.RW,
    }

    return RegisterBitfield(
        name=_get_attr(elem, "id"),
        description=_get_attr(elem, "description").strip(),
        bit_offset=int(_get_attr(elem, "end")),
        bit_width=int(_get_attr(elem, "width")),
        rw_access=rw_access_mapping[_get_attr(elem, "rwaccess")],
        reset_value=int(_get_attr(elem, "resetval"), base=16),
    )


def _parse_register(elem: et.Element) -> Register:
    return Register(
        name=_get_attr(elem, "id"),
        description=_get_attr(elem, "description").strip(),
        bit_width=int(_get_attr(elem, "width")),
        address_offset=int(_get_attr(elem, "offset"), base=16),
        bitfields=[_parse_register_bitfield(x) for x in elem.iter("bitfield")],
    )


def _parse_peripheral_instance(elem: et.Element, definition_name: str) -> PeripheralInstance:
    name = _get_attr(elem, "id")

    try:
        index = int(name.removeprefix(definition_name))
    except ValueError:
        index = None

    return PeripheralInstance(
        name=name,
        index=index,
        address=int(_get_attr(elem, "baseaddr"), base=16),
        size=int(_get_attr(elem, "size"), base=16),
    )


def _parse_peripheral_definition(
    path: pathlib.Path,
    instance_elems: list[et.Element],
) -> PeripheralDefinition:
    tree = et.parse(path)
    root_elem = tree.getroot()

    name = _get_attr(root_elem, "id")

    try:
        return PeripheralDefinition(
            name=name,
            description=_get_attr(root_elem, "description").strip(),
            registers=[_parse_register(x) for x in root_elem.iter("register")],
            instances=[_parse_peripheral_instance(elem, name) for elem in instance_elems],
        )
    except Exception:
        print(f"Error while processing {path}")
        raise


def parse_device(path: pathlib.Path) -> Device:
    """Parse device from XML definition."""
    tree = et.parse(path)
    root_elem = tree.getroot()

    cpu_elem = next(root_elem.iter("cpu"))

    instance_dict: defaultdict[pathlib.Path, list[et.Element]] = defaultdict(list)
    for instance in cpu_elem.iter("instance"):
        instance_dict[pathlib.Path(_get_attr(instance, "href"))].append(instance)

    try:
        return Device(
            part_number=_get_attr(root_elem, "partnum"),
            cpu_name=_get_attr(cpu_elem, "id"),
            peripherals=[
                _parse_peripheral_definition(path.parent / periph_path, instances)
                for periph_path, instances in instance_dict.items()
            ],
        )
    except Exception:
        print(f"Error while processing {path}")
        raise
