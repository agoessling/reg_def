import dataclasses
import enum

class RwAccess(enum.Enum):
  RO = enum.auto()
  WO = enum.auto()
  RW = enum.auto()

@dataclasses.dataclass
class RegisterBitfield:
  name: str
  description: str
  bit_offset: int
  bit_width: int
  rw_access: RwAccess
  reset_value: int

@dataclasses.dataclass
class Register:
  name: str
  description: str
  bit_width: int
  address_offset: int
  bit_fields: list[RegisterBitfield]

@dataclasses.dataclass
class PeripheralInstance:
  name: str
  index: int | None
  address: int
  size: int

@dataclasses.dataclass
class PeripheralDefinition:
  name: str
  description: str
  registers: list[Register]
  instances: list[PeripheralInstance]

@dataclasses.dataclass
class Device:
  part_number: str
  cpu_name: str
  peripherals: list[PeripheralDefinition]
