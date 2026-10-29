import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .model import InputError, json_bytes, load
from .render import compile_design
from .validation import validate


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compile consistent routed-network documentation.")
    parser.add_argument(
        "--version", action="version", version=f"network-design-compiler {__version__}"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "build"):
        command = commands.add_parser(name)
        command.add_argument("--input", type=Path, required=True)
        if name == "build":
            command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        data, source_hash = load(args.input)
        if args.command == "validate":
            result = validate(data)
            print(json_bytes(result).decode(), end="")
            return 0 if result["valid"] else 1
        files, result = compile_design(data, source_hash)
        args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
        for name, raw in files.items():
            descriptor = os.open(args.output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(raw)
        warnings = sum(f["severity"] == "warning" for f in result["findings"])
        print(
            f"{'VALID MODEL' if result['valid'] else 'INVALID MODEL'} | "
            f"{len(files)} artifacts | {warnings} warnings | offline-design-consistency"
        )
        return 0 if result["valid"] else 1
    except InputError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
    except FileExistsError:
        print("Output exists; choose a new directory. No files overwritten.", file=sys.stderr)
    except OSError:
        print(
            "File operation failed. Check paths and permissions. Partial output may remain; "
            "a complete manifest and matching hashes are required before use.",
            file=sys.stderr,
        )
    return 2


if __name__ == "__main__":
    sys.exit(main())
