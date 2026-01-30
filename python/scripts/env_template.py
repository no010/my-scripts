from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_SENSITIVE_PATTERNS = [
    r".*password.*",
    r".*secret.*",
    r".*token.*",
    r".*key.*",
    r".*api.*",
    r".*auth.*",
    r".*credential.*",
    r".*private.*",
]


def is_sensitive_key(key: str, patterns: list[str] | None = None) -> bool:
    patterns = patterns or DEFAULT_SENSITIVE_PATTERNS
    key_lower = key.lower()
    for pattern in patterns:
        if re.match(pattern, key_lower, re.IGNORECASE):
            return True
    return False


def generate_template(
    env_path: Path,
    output_path: Path | None = None,
    placeholder: str = "YOUR_VALUE_HERE",
    patterns: list[str] | None = None,
    keep_values: bool = False,
) -> str:
    if not env_path.exists():
        raise FileNotFoundError(f"Environment file not found: {env_path}")

    lines = []
    with env_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n\r")
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                lines.append(line)
                continue

            if "=" in stripped:
                key, _, value = stripped.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")

                if keep_values:
                    lines.append(f"{key}={value}")
                elif is_sensitive_key(key, patterns):
                    lines.append(f"{key}={placeholder}")
                else:
                    lines.append(f"{key}={value}")
            else:
                lines.append(line)

    template_content = "\n".join(lines) + "\n"

    if output_path:
        output_path.write_text(template_content, encoding="utf-8")

    return template_content


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate .env.template from .env file (removes sensitive values)"
    )
    parser.add_argument("input", type=Path, help="Input .env file path")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output template file path (default: input.template)",
    )
    parser.add_argument(
        "-p",
        "--placeholder",
        default="YOUR_VALUE_HERE",
        help="Placeholder text for sensitive values",
    )
    parser.add_argument(
        "--keep-values",
        action="store_true",
        help="Keep all values (don't mask sensitive data)",
    )
    parser.add_argument(
        "--pattern",
        action="append",
        dest="patterns",
        help="Additional regex patterns for sensitive keys (can be used multiple times)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print to stdout instead of writing file",
    )

    args = parser.parse_args(argv)

    output_path = args.output
    if not output_path and not args.dry_run:
        output_path = args.input.with_suffix(".template")

    try:
        patterns = args.patterns if args.patterns else None
        template = generate_template(
            args.input,
            output_path if not args.dry_run else None,
            args.placeholder,
            patterns,
            args.keep_values,
        )

        if args.dry_run:
            print(template)
        else:
            print(f"Template generated: {output_path}")

        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
