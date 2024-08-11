"""Types which describe a device's address space."""

import dataclasses
import enum
from typing import Protocol


class _HasName(Protocol):
    @property
    def name(self) -> str: ...


def _assert_name(obj: _HasName) -> None:
    if not obj.name:
        msg = f"{obj.__class__.__name__} is missing name."
        raise ValueError(msg)


def _assert_positive(val: float, name: str, parent: str) -> None:
    if val < 0:
        msg = f"{name.capitalize()} ({val}) is negative in {parent}."
        raise ValueError(msg)


class RwAccess(enum.Enum):
    """Access permissions."""

    RO = enum.auto()
    WO = enum.auto()
    RW = enum.auto()


@dataclasses.dataclass(frozen=True)
class RegisterBitfield:
    """Register Bitfield."""

    name: str
    description: str
    bit_offset: int
    bit_width: int
    rw_access: RwAccess
    reset_value: int

    def __post_init__(self) -> None:
        """Post init."""
        _assert_name(self)

        _assert_positive(self.bit_offset, "bit offset", self.name)
        _assert_positive(self.bit_width, "bit width", self.name)
        _assert_positive(self.reset_value, "reset value", self.name)

        if self.reset_value >= 2**self.bit_width:
            msg = f"Reset value ({self.reset_value}) too large in {self.name}"
            raise ValueError(msg)


@dataclasses.dataclass(frozen=True)
class Register:
    """Register."""

    name: str
    description: str
    bit_width: int
    address_offset: int
    bitfields: list[RegisterBitfield]

    def __post_init__(self) -> None:
        """Post init."""
        _assert_name(self)

        if self.bit_width not in [8, 16, 32, 64]:
            msg = f"Invalid bit width ({self.bit_width}) in {self.name}"
            raise ValueError(msg)

        _assert_positive(self.address_offset, "address offset", self.name)
        if self.address_offset % (self.bit_width // 8) != 0:
            msg = f"Unaligned address offset ({self.address_offset:#010x}) in {self.name}"
            raise ValueError(msg)

        # Sort bitfields.
        self.bitfields.sort(key=lambda x: x.bit_offset)

        offset = 0
        for bitfield in self.bitfields:
            if bitfield.bit_offset < offset:
                msg = f"Overlapping bitfield ({bitfield.name}) in {self.name}."
                raise ValueError(msg)
            offset = bitfield.bit_offset + bitfield.bit_width

        if offset > self.bit_width:
            msg = f"Bit width ({offset}) overflowed in {self.name} ({self.bit_width})"
            raise ValueError(msg)


@dataclasses.dataclass(frozen=True)
class PeripheralInstance:
    """Instance of Device Peripheral."""

    name: str
    index: int | None
    address: int
    size: int

    def __post_init__(self) -> None:
        """Post init."""
        _assert_name(self)

        if self.index is not None:
            _assert_positive(self.index, "index", self.name)
        _assert_positive(self.address, "address", self.name)
        _assert_positive(self.size, "size", self.name)


@dataclasses.dataclass(frozen=True)
class PeripheralDefinition:
    """Definition of Device Peripheral."""

    name: str
    description: str
    registers: list[Register]
    instances: list[PeripheralInstance]

    def __post_init__(self) -> None:
        """Post init."""
        _assert_name(self)

        # Sort registers.
        # NOTE: registers addresses are allowed to overlap to support read vs. write aliases.
        self.registers.sort(key=lambda x: x.address_offset)

        if self.registers and self.instances:
            last_register = self.registers[-1]
            instance = self.instances[0]
            if last_register.address_offset + last_register.bit_width // 8 > instance.size:
                msg = f"Registers overflowed peripheral size in {self.name}."
                raise ValueError(msg)

        # Sort instances.
        self.instances.sort(key=lambda x: x.address)

        index_set = set()
        for instance in self.instances:
            if instance.index is not None and instance.index in index_set:
                msg = f"Duplicate index for instance ({instance.name}) in {self.name}."
                raise ValueError(msg)
            index_set.add(instance.index)

            if instance.size != self.instances[0].size:
                msg = (
                    "Peripheral size mismatch between "
                    f"{instance.name} and {self.instances[0].name}."
                )
                raise ValueError(msg)


@dataclasses.dataclass(frozen=True)
class Device:
    """Device."""

    part_number: str
    cpu_name: str
    peripherals: list[PeripheralDefinition]
