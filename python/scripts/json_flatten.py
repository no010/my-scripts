from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def flatten(
    data: dict[str, Any],
    separator: str = ".",
    prefix: str = "",
    max_depth: int | None = None,
    current_depth: int = 0,
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in data.items():
        new_key = f"{prefix}{separator}{key}" if prefix else key

        if max_depth is not None and current_depth >= max_depth:
            result[new_key] = value
        elif isinstance(value, dict):
            nested = flatten(value, separator, new_key, max_depth, current_depth + 1)
            result.update(nested)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                list_key = f"{new_key}{separator}{i}"
                if isinstance(item, dict):
                    nested = flatten(
                        item, separator, list_key, max_depth, current_depth + 1
                    )
                    result.update(nested)
                elif isinstance(item, list):
                    nested = flatten(
                        {str(i): item}, separator, new_key, max_depth, current_depth + 1
                    )
                    result.update(nested)
                else:
                    result[list_key] = item
        else:
            result[new_key] = value

    return result


def unflatten(data: dict[str, Any], separator: str = ".") -> dict[str, Any] | list[Any]:
    result: dict[str, Any] = {}

    for key, value in data.items():
        parts = key.split(separator)
        current: Any = result

        for i, part in enumerate(parts[:-1]):
            next_part = parts[i + 1] if i + 1 < len(parts) - 1 else None
            is_next_index = next_part is not None and next_part.isdigit()

            if part.isdigit():
                index = int(part)
                if not isinstance(current, list):
                    return result
                while len(current) <= index:
                    current.append({} if not is_next_index else [])
                if is_next_index and not isinstance(current[index], list):
                    current[index] = []
                elif not is_next_index and not isinstance(current[index], dict):
                    current[index] = {}
                current = current[index]
            else:
                if part not in current:
                    current[part] = [] if is_next_index else {}
                current = current[part]

        last_part = parts[-1]
        if last_part.isdigit():
            index = int(last_part)
            if not isinstance(current, list):
                return result
            while len(current) <= index:
                current.append(None)
            current[index] = value
        else:
            if not isinstance(current, dict):
                return result
            current[last_part] = value

    return result


def process_file(
    input_path: Path,
    output_path: Path | None,
    mode: str,
    separator: str = ".",
    max_depth: int | None = None,
) -> str:
    with input_path.open(encoding="utf-8") as f:
        data = json.load(f)

    if mode == "flatten":
        if not isinstance(data, dict):
            raise ValueError("Input must be a JSON object for flatten mode")
        result = flatten(data, separator, max_depth=max_depth)
    elif mode == "unflatten":
        if not isinstance(data, dict):
            raise ValueError("Input must be a JSON object for unflatten mode")
        result = unflatten(data, separator)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    output = json.dumps(result, ensure_ascii=False, indent=2)

    if output_path:
        output_path.write_text(output, encoding="utf-8")

    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flatten or unflatten JSON data")
    parser.add_argument("input", type=Path, help="Input JSON file")
    parser.add_argument("-o", "--output", type=Path, help="Output JSON file")
    parser.add_argument(
        "-m",
        "--mode",
        choices=["flatten", "unflatten"],
        required=True,
        help="Operation mode",
    )
    parser.add_argument(
        "-s", "--separator", default=".", help="Key separator (default: .)"
    )
    parser.add_argument(
        "-d",
        "--max-depth",
        type=int,
        help="Maximum depth for flattening (default: unlimited)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print to stdout instead of writing file"
    )

    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: File not found: {args.input}")
        return 1

    try:
        output = process_file(
            args.input,
            args.output if not args.dry_run else None,
            args.mode,
            args.separator,
            args.max_depth,
        )

        if args.dry_run or not args.output:
            print(output)
        else:
            print(f"Output saved to: {args.output}")

        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
