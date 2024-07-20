import dataclasses
import enum


def assert_positive(val: int | float, name: str, parent: str):
  if val < 0:
    raise ValueError(f'{name.capitalize()} ({val}) is negative in {parent}.')


class RwAccess(enum.Enum):
  RO = enum.auto()
  WO = enum.auto()
  RW = enum.auto()


@dataclasses.dataclass(frozen=True)
class RegisterBitfield:
  name: str
  description: str
  bit_offset: int
  bit_width: int
  rw_access: RwAccess
  reset_value: int

  def __post_init__(self):
    assert_positive(self.bit_offset, 'bit offset', self.name)
    assert_positive(self.bit_width, 'bit width', self.name)
    assert_positive(self.reset_value, 'reset value', self.name)

    if self.reset_value >= 2**self.bit_width:
      raise ValueError(f'Reset value ({self.reset_value}) too large in {self.name}')


@dataclasses.dataclass(frozen=True)
class Register:
  name: str
  description: str
  bit_width: int
  address_offset: int
  bitfields: list[RegisterBitfield]

  def __post_init__(self):
    if self.bit_width not in [8, 16, 32, 64]:
      raise ValueError(f'Invalid bit width ({self.bit_width}) in {self.name}')

    assert_positive(self.address_offset, 'address offset', self.name)
    if self.address_offset % (self.bit_width // 8) != 0:
      raise ValueError(f'Unaligned address offset ({self.address_offset:#010x}) in {self.name}')

    # Sort bitfields.
    self.bitfields.sort(key=lambda x: x.bit_offset)

    offset = 0
    for bitfield in self.bitfields:
      if bitfield.bit_offset < offset:
        raise ValueError(f'Overlapping bitfield ({bitfield.name}) in {self.name}.')
      offset = bitfield.bit_offset + bitfield.bit_width

    if offset > self.bit_width:
      raise ValueError(f'Bit width ({self.bit_width}) overflowed in {self.name}')


@dataclasses.dataclass(frozen=True)
class PeripheralInstance:
  name: str
  index: int | None
  address: int
  size: int

  def __post_init__(self):
    if self.index is not None:
      assert_positive(self.index, 'index', self.name)
    assert_positive(self.address, 'address', self.name)
    assert_positive(self.size, 'size', self.name)


@dataclasses.dataclass(frozen=True)
class PeripheralDefinition:
  name: str
  description: str
  registers: list[Register]
  instances: list[PeripheralInstance]

  def __post_init__(self):
    # Sort registers.
    # NOTE: registers addresses are allowed to overlap to support read vs. write aliases.
    self.registers.sort(key=lambda x: x.address_offset)

    if self.registers and self.instances:
      last_register = self.registers[-1]
      instance = self.instances[0]
      if last_register.address_offset + last_register.bit_width // 8 > instance.size:
        raise ValueError(f'Registers overflowed peripheral size in {self.name}.')

    # Sort instances.
    self.instances.sort(key=lambda x: x.address)

    index_set = set()
    for instance in self.instances:
      if instance.index is not None and instance.index in index_set:
        raise ValueError(f'Duplicate index for instance ({instance.name}) in {self.name}.')
      index_set.add(instance.index)

      if instance.size != self.instances[0].size:
        raise ValueError(
            f'Peripheral size mismatch between {instance.name} and {self.instances[0].name}.')


@dataclasses.dataclass(frozen=True)
class Device:
  part_number: str
  cpu_name: str
  peripherals: list[PeripheralDefinition]
