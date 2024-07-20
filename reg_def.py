import argparse
import pathlib

import ti_parser


def main() -> None:
  parser = argparse.ArgumentParser(
      description='Code generate register definitions from various definition files.')

  parser.add_argument('--definition', required=True, type=pathlib.Path, help='Register definition file.')

  args = parser.parse_args()

  device = ti_parser.parse_device(args.definition)
  print(device)


if __name__ == '__main__':
  main()
