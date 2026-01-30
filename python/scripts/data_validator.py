from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class ValidationRule:
    field: str
    required: bool = False
    type_: str | None = None
    pattern: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    unique: bool = False
    custom: Callable[[Any], bool] | None = None
    error_message: str = ""


@dataclass
class ValidationResult:
    valid: bool
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    errors: list[dict] = field(default_factory=list)
    duplicates: list[dict] = field(default_factory=list)


def validate_email(value: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, str(value)))


def validate_url(value: str) -> bool:
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return bool(re.match(pattern, str(value), re.IGNORECASE))


def validate_date(value: str, fmt: str = "%Y-%m-%d") -> bool:
    from datetime import datetime

    try:
        datetime.strptime(str(value), fmt)
        return True
    except ValueError:
        return False


TYPE_VALIDATORS: dict[str, Callable[[Any], bool]] = {
    "int": lambda x: isinstance(x, int) or (isinstance(x, str) and x.isdigit()),
    "float": lambda x: isinstance(x, (int, float))
    or (isinstance(x, str) and x.replace(".", "").isdigit()),
    "bool": lambda x: isinstance(x, bool)
    or str(x).lower() in ("true", "false", "1", "0"),
    "email": validate_email,
    "url": validate_url,
    "date": validate_date,
    "string": lambda x: isinstance(x, str),
}


def validate_csv(
    file_path: Path,
    rules: list[ValidationRule],
    encoding: str = "utf-8",
    skip_header: bool = False,
) -> ValidationResult:
    result = ValidationResult(valid=True)
    seen_values: dict[str, set] = {}

    with file_path.open(encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2 if skip_header else 1):
            result.total_rows += 1
            row_valid = True
            row_errors = []

            for rule in rules:
                value = row.get(rule.field)

                if rule.required and (value is None or str(value).strip() == ""):
                    row_valid = False
                    row_errors.append(f"Field '{rule.field}' is required")
                    continue

                if value is None or str(value).strip() == "":
                    continue

                if rule.type_ and rule.type_ in TYPE_VALIDATORS:
                    if not TYPE_VALIDATORS[rule.type_](value):
                        row_valid = False
                        type_name = rule.type_
                        row_errors.append(
                            f"Field '{rule.field}' must be a valid {type_name}"
                        )

                if rule.pattern:
                    if not re.match(rule.pattern, str(value)):
                        row_valid = False
                        row_errors.append(
                            f"Field '{rule.field}' does not match pattern"
                        )

                if rule.type_ in ("int", "float"):
                    try:
                        num_value = float(value)
                        if rule.min_value is not None and num_value < rule.min_value:
                            row_valid = False
                            row_errors.append(
                                f"Field '{rule.field}' must be >= {rule.min_value}"
                            )
                        if rule.max_value is not None and num_value > rule.max_value:
                            row_valid = False
                            row_errors.append(
                                f"Field '{rule.field}' must be <= {rule.max_value}"
                            )
                    except ValueError:
                        pass

                if rule.unique:
                    if rule.field not in seen_values:
                        seen_values[rule.field] = set()
                    if value in seen_values[rule.field]:
                        result.duplicates.append(
                            {"row": row_num, "field": rule.field, "value": value}
                        )
                    seen_values[rule.field].add(value)

                if rule.custom and not rule.custom(value):
                    row_valid = False
                    msg = (
                        rule.error_message
                        or f"Field '{rule.field}' failed custom validation"
                    )
                    row_errors.append(msg)

            if row_valid:
                result.valid_rows += 1
            else:
                result.invalid_rows += 1
                result.errors.append({"row": row_num, "errors": row_errors})

    result.valid = result.invalid_rows == 0 and len(result.duplicates) == 0
    return result


def validate_json(
    file_path: Path,
    rules: list[ValidationRule],
    encoding: str = "utf-8",
) -> ValidationResult:
    with file_path.open(encoding=encoding) as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("JSON must be an array of objects")

    result = ValidationResult(valid=True)
    seen_values: dict[str, set] = {}

    for row_num, item in enumerate(data, start=1):
        result.total_rows += 1
        row_valid = True
        row_errors = []

        for rule in rules:
            value = item.get(rule.field)

            if rule.required and (value is None or str(value).strip() == ""):
                row_valid = False
                row_errors.append(f"Field '{rule.field}' is required")
                continue

            if value is None or str(value).strip() == "":
                continue

            if rule.type_ and rule.type_ in TYPE_VALIDATORS:
                if not TYPE_VALIDATORS[rule.type_](value):
                    row_valid = False
                    type_name = rule.type_
                    row_errors.append(
                        f"Field '{rule.field}' must be a valid {type_name}"
                    )

            if rule.pattern:
                if not re.match(rule.pattern, str(value)):
                    row_valid = False
                    row_errors.append(f"Field '{rule.field}' does not match pattern")

            if rule.unique:
                if rule.field not in seen_values:
                    seen_values[rule.field] = set()
                if value in seen_values[rule.field]:
                    result.duplicates.append(
                        {"row": row_num, "field": rule.field, "value": value}
                    )
                seen_values[rule.field].add(value)

        if row_valid:
            result.valid_rows += 1
        else:
            result.invalid_rows += 1
            result.errors.append({"row": row_num, "errors": row_errors})

    result.valid = result.invalid_rows == 0 and len(result.duplicates) == 0
    return result


def parse_rules(rules_str: list[str]) -> list[ValidationRule]:
    rules = []
    for rule_str in rules_str:
        parts = rule_str.split(":")
        field = parts[0]
        rule = ValidationRule(field=field)

        for part in parts[1:]:
            if part == "required":
                rule.required = True
            elif part.startswith("type="):
                rule.type_ = part[5:]
            elif part.startswith("pattern="):
                rule.pattern = part[8:]
            elif part.startswith("min="):
                rule.min_value = float(part[4:])
            elif part.startswith("max="):
                rule.max_value = float(part[4:])
            elif part == "unique":
                rule.unique = True

        rules.append(rule)

    return rules


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate CSV or JSON data files")
    parser.add_argument("file", type=Path, help="Input file to validate")
    parser.add_argument(
        "-f",
        "--format",
        choices=["csv", "json"],
        help="File format (auto-detected if not specified)",
    )
    parser.add_argument(
        "-r",
        "--rule",
        action="append",
        required=True,
        help="Validation rule (format: field:required:type=email:unique)",
    )
    parser.add_argument("--encoding", default="utf-8", help="File encoding")
    parser.add_argument("--output", type=Path, help="Output error report to file")
    parser.add_argument("--strict", action="store_true", help="Fail on any error")

    args = parser.parse_args(argv)

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        return 1

    file_format = args.format or args.file.suffix.lower().lstrip(".")
    if file_format not in ("csv", "json"):
        print(f"Error: Unsupported file format: {file_format}")
        return 1

    try:
        rules = parse_rules(args.rule)

        if file_format == "csv":
            result = validate_csv(args.file, rules, args.encoding)
        else:
            result = validate_json(args.file, rules, args.encoding)

        print(f"Total rows: {result.total_rows}")
        print(f"Valid rows: {result.valid_rows}")
        print(f"Invalid rows: {result.invalid_rows}")

        if result.duplicates:
            print(f"\nDuplicate values found: {len(result.duplicates)}")
            for dup in result.duplicates[:10]:
                print(f"  Row {dup['row']}: {dup['field']} = {dup['value']}")
            if len(result.duplicates) > 10:
                print(f"  ... and {len(result.duplicates) - 10} more")

        if result.errors:
            print(f"\nValidation errors:")
            for error in result.errors[:10]:
                print(f"  Row {error['row']}:")
                for err in error["errors"]:
                    print(f"    - {err}")
            if len(result.errors) > 10:
                print(f"  ... and {len(result.errors) - 10} more errors")

        if args.output and (result.errors or result.duplicates):
            report = {
                "file": str(args.file),
                "total_rows": result.total_rows,
                "valid_rows": result.valid_rows,
                "invalid_rows": result.invalid_rows,
                "duplicates": result.duplicates,
                "errors": result.errors,
            }
            with args.output.open("w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\nError report saved to: {args.output}")

        if args.strict and (result.errors or result.duplicates):
            return 1

        return 0 if result.valid else 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
