from __future__ import annotations

import argparse
import json
from pathlib import Path


def convert_yaml_to_json(yaml_path: Path, json_path: Path, indent: int = 2) -> None:
    try:
        import yaml
    except ImportError:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")

    with yaml_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def convert_json_to_yaml(json_path: Path, yaml_path: Path) -> None:
    try:
        import yaml
    except ImportError:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")

    with json_path.open(encoding="utf-8") as f:
        data = json.load(f)

    with yaml_path.open("w", encoding="utf-8") as f:
        yaml.dump(
            data, f, default_flow_style=False, allow_unicode=True, sort_keys=False
        )


def batch_convert(
    input_dir: Path,
    output_dir: Path,
    source_format: str,
    target_format: str,
    indent: int = 2,
) -> dict:
    if source_format == "yaml":
        pattern = "*.yaml"
        pattern_alt = "*.yml"
    elif source_format == "json":
        pattern = "*.json"
        pattern_alt = None
    else:
        raise ValueError(f"Unknown source format: {source_format}")

    files = list(input_dir.glob(pattern))
    if pattern_alt:
        files.extend(input_dir.glob(pattern_alt))

    stats = {"processed": 0, "failed": 0, "errors": []}

    output_dir.mkdir(parents=True, exist_ok=True)

    for input_file in files:
        try:
            if target_format == "json":
                output_file = output_dir / f"{input_file.stem}.json"
                convert_yaml_to_json(input_file, output_file, indent)
            elif target_format == "yaml":
                output_file = output_dir / f"{input_file.stem}.yaml"
                convert_json_to_yaml(input_file, output_file)
            else:
                raise ValueError(f"Unknown target format: {target_format}")

            stats["processed"] += 1
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(f"{input_file}: {e}")

    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert between YAML and JSON formats"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    single_parser = subparsers.add_parser("convert", help="Convert single file")
    single_parser.add_argument("input", type=Path, help="Input file path")
    single_parser.add_argument("output", type=Path, help="Output file path")
    single_parser.add_argument(
        "--indent", type=int, default=2, help="JSON indentation (default: 2)"
    )

    batch_parser = subparsers.add_parser("batch", help="Batch convert directory")
    batch_parser.add_argument("input_dir", type=Path, help="Input directory")
    batch_parser.add_argument("output_dir", type=Path, help="Output directory")
    batch_parser.add_argument(
        "--from",
        dest="source_format",
        choices=["yaml", "json"],
        required=True,
        help="Source format",
    )
    batch_parser.add_argument(
        "--to",
        dest="target_format",
        choices=["yaml", "json"],
        required=True,
        help="Target format",
    )
    batch_parser.add_argument(
        "--indent", type=int, default=2, help="JSON indentation (default: 2)"
    )

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    try:
        if args.command == "convert":
            input_ext = args.input.suffix.lower()
            output_ext = args.output.suffix.lower()

            if input_ext in (".yaml", ".yml") and output_ext == ".json":
                convert_yaml_to_json(args.input, args.output, args.indent)
                print(f"Converted: {args.input} -> {args.output}")
            elif input_ext == ".json" and output_ext in (".yaml", ".yml"):
                convert_json_to_yaml(args.input, args.output)
                print(f"Converted: {args.input} -> {args.output}")
            else:
                print(f"Error: Unsupported conversion {input_ext} -> {output_ext}")
                return 1

        elif args.command == "batch":
            stats = batch_convert(
                args.input_dir,
                args.output_dir,
                args.source_format,
                args.target_format,
                args.indent,
            )

            print(f"Files processed: {stats['processed']}")
            print(f"Files failed: {stats['failed']}")

            if stats["errors"]:
                print("\nErrors:")
                for error in stats["errors"]:
                    print(f"  - {error}")

        return 0
    except ImportError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
