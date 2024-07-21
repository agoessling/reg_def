import argparse
import pathlib

import c_generator
import ti_parser


def main() -> None:
  parser = argparse.ArgumentParser(
      description='Code generate register definitions from various definition files.')

  parser.add_argument('--definition', required=True, type=pathlib.Path,
                      help='Register definition file.')
  parser.add_argument('--output', required=True, type=pathlib.Path, help='Generated header file.')

  args = parser.parse_args()

  device = ti_parser.parse_device(args.definition)

  c_generator.generate_header(args.output, device)


if __name__ == '__main__':
  main()
