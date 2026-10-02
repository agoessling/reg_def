"""Generate device register definitions."""

import argparse
import pathlib

from src import c_generator, rust_generator, ti_parser


def main() -> None:
    """Execute the name function."""
    parser = argparse.ArgumentParser(
        description="Code generate register definitions from various definition files."
    )

    definition_group = parser.add_mutually_exclusive_group(required=True)

    definition_group.add_argument("--ti_xml", type=pathlib.Path, help="TI XML definition file.")

    parser.add_argument("--output", required=True, type=pathlib.Path, help="Generated source file.")

    parser.add_argument("--language", choices=("c", "rust"), default="c")

    args = parser.parse_args()

    if args.ti_xml:
        device = ti_parser.parse_device(args.ti_xml)
    else:
        raise RuntimeError

    if args.language == "rust":
        rust_generator.generate_source(args.output, device)
    else:
        c_generator.generate_header(args.output, device)


if __name__ == "__main__":
    main()
