from __future__ import annotations

import argparse

from .api import TextECode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="textecode")
    subparsers = parser.add_subparsers(dest="command", required=True)

    version_parser = subparsers.add_parser("version")
    version_parser.add_argument("--dll", dest="dll_path")

    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("input_e_file")
    generate_parser.add_argument("output_project_file")
    generate_parser.add_argument("--dll", dest="dll_path")

    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("input_project_file")
    restore_parser.add_argument("output_e_file")
    restore_parser.add_argument("--dll", dest="dll_path")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    client = TextECode(getattr(args, "dll_path", None))

    if args.command == "version":
        print(client.version())
        return 0
    if args.command == "generate":
        print(client.generate(args.input_e_file, args.output_project_file))
        return 0
    if args.command == "restore":
        print(client.restore(args.input_project_file, args.output_e_file))
        return 0
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
