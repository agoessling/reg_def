from collections import defaultdict
import pathlib
import xml.etree.ElementTree as et

from device_types import RwAccess, Device, PeripheralInstance, PeripheralDefinition, Register, RegisterBitfield


def get_attr(element: et.Element, attr: str) -> str:
  val = element.get(attr)
  if val is None:
    raise KeyError(f'No attribute "{attr}" in {element.tag}')
  return val


def parse_register_bitfield(elem: et.Element) -> RegisterBitfield:
  rw_access_mapping = {
      'R': RwAccess.RO,
      'RO': RwAccess.RO,
      'W': RwAccess.WO,
      'WO': RwAccess.WO,
      '': RwAccess.RW,
      'RW': RwAccess.RW,
  }

  return RegisterBitfield(
      name=get_attr(elem, 'id'),
      description=get_attr(elem, 'description'),
      bit_offset=int(get_attr(elem, 'end')),
      bit_width=int(get_attr(elem, 'width')),
      rw_access=rw_access_mapping[get_attr(elem, 'rwaccess')],
      reset_value=int(get_attr(elem, 'resetval'), base=16),
  )


def parse_register(elem: et.Element) -> Register:
  return Register(
      name=get_attr(elem, 'id'),
      description=get_attr(elem, 'description'),
      bit_width=int(get_attr(elem, 'width')),
      address_offset=int(get_attr(elem, 'offset'), base=16),
      bitfields=[parse_register_bitfield(x) for x in elem.iter('bitfield')],
  )


def parse_peripheral_instance(elem: et.Element, definition_name: str) -> PeripheralInstance:
  name = get_attr(elem, 'id')

  try:
    index = int(name.removeprefix(definition_name))
  except ValueError:
    index = None

  return PeripheralInstance(
      name=name,
      index=index,
      address=int(get_attr(elem, 'baseaddr'), base=16),
      size=int(get_attr(elem, 'size'), base=16),
  )


def parse_peripheral_definition(
    path: pathlib.Path,
    instance_elems: list[et.Element],
) -> PeripheralDefinition:
  tree = et.parse(path)
  root_elem = tree.getroot()

  name = get_attr(root_elem, 'id')

  try:
    return PeripheralDefinition(
        name=name,
        description=get_attr(root_elem, 'description'),
        registers=[parse_register(x) for x in root_elem.iter('register')],
        instances=[parse_peripheral_instance(elem, name) for elem in instance_elems],
    )
  except Exception as e:
    print(f'Error while processing {path}')
    raise e


def parse_device(path: pathlib.Path) -> Device:
  tree = et.parse(path)
  root_elem = tree.getroot()

  cpu_elem = next(root_elem.iter('cpu'))

  instance_dict: defaultdict[pathlib.Path, list[et.Element]] = defaultdict(list)
  for instance in cpu_elem.iter('instance'):
    instance_dict[pathlib.Path(get_attr(instance, 'href'))].append(instance)

  try:
    return Device(
        part_number=get_attr(root_elem, 'partnum'),
        cpu_name=get_attr(cpu_elem, 'id'),
        peripherals=[
            parse_peripheral_definition(path.parent / periph_path, instances)
            for periph_path, instances in instance_dict.items()
        ],
    )
  except Exception as e:
    print(f'Error while processing {path}')
    raise e
