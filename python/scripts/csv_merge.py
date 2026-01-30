from __future__ import annotations

import argparse
import csv
from pathlib import Path


def merge_csv_files(
    input_files: list[Path],
    output_file: Path,
    merge_mode: str = "rows",
    add_source: bool = False,
    deduplicate: bool = False,
    encoding: str = "utf-8",
) -> dict:
    if not input_files:
        raise ValueError("No input files provided")

    for f in input_files:
        if not f.exists():
            raise FileNotFoundError(f"File not found: {f}")

    stats = {
        "files_processed": 0,
        "rows_total": 0,
        "rows_written": 0,
        "duplicates_removed": 0,
    }

    if merge_mode == "rows":
        stats = _merge_by_rows(
            input_files, output_file, add_source, deduplicate, encoding, stats
        )
    elif merge_mode == "columns":
        stats = _merge_by_columns(
            input_files, output_file, add_source, deduplicate, encoding, stats
        )
    else:
        raise ValueError(f"Unknown merge mode: {merge_mode}")

    return stats


def _merge_by_rows(
    input_files: list[Path],
    output_file: Path,
    add_source: bool,
    deduplicate: bool,
    encoding: str,
    stats: dict,
) -> dict:
    all_rows = []
    fieldnames: list[str] | None = None
    seen_rows: set[tuple[tuple[str, str], ...]] = set()

    for input_file in input_files:
        with input_file.open(encoding=encoding, newline="") as f:
            reader = csv.DictReader(f)
            if fieldnames is None:
                fieldnames = list(reader.fieldnames) if reader.fieldnames else []
                if add_source:
                    fieldnames = ["_source_file"] + fieldnames

            for row in reader:
                stats["rows_total"] += 1

                if add_source:
                    row["_source_file"] = input_file.name

                if deduplicate:
                    row_tuple = tuple(sorted(row.items()))
                    if row_tuple in seen_rows:
                        stats["duplicates_removed"] += 1
                        continue
                    seen_rows.add(row_tuple)

                all_rows.append(row)

        stats["files_processed"] += 1

    with output_file.open("w", encoding=encoding, newline="") as f:
        if fieldnames is None:
            fieldnames = []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
        stats["rows_written"] = len(all_rows)

    return stats


def _merge_by_columns(
    input_files: list[Path],
    output_file: Path,
    add_source: bool,
    deduplicate: bool,
    encoding: str,
    stats: dict,
) -> dict:
    all_data: list[tuple[str, list[dict[str, str]], list[str]]] = []
    row_count: int | None = None

    for input_file in input_files:
        with input_file.open(encoding=encoding, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            if row_count is None:
                row_count = len(rows)
            elif len(rows) != row_count:
                raise ValueError(
                    f"Row count mismatch: {input_file} has {len(rows)} rows, "
                    f"expected {row_count}"
                )

            all_data.append(
                (
                    input_file.name,
                    rows,
                    list(reader.fieldnames) if reader.fieldnames else [],
                )
            )

        stats["files_processed"] += 1

    if row_count is None:
        row_count = 0

    merged_rows = []
    seen_rows: set[tuple[tuple[str, str], ...]] = set()

    for i in range(row_count):
        merged_row: dict[str, str] = {}
        for filename, rows, fieldnames in all_data:
            for key, value in rows[i].items():
                if len(all_data) > 1:
                    new_key = f"{Path(filename).stem}.{key}"
                else:
                    new_key = key
                merged_row[new_key] = value

        if add_source:
            merged_row["_merge_index"] = str(i + 1)

        if deduplicate:
            row_tuple = tuple(sorted(merged_row.items()))
            if row_tuple in seen_rows:
                stats["duplicates_removed"] += 1
                continue
            seen_rows.add(row_tuple)

        merged_rows.append(merged_row)
        stats["rows_total"] += 1

    all_fieldnames: list[str] = []
    for filename, _, fieldnames in all_data:
        if len(all_data) > 1:
            all_fieldnames.extend([f"{Path(filename).stem}.{f}" for f in fieldnames])
        else:
            all_fieldnames.extend(fieldnames)

    if add_source:
        all_fieldnames.append("_merge_index")

    with output_file.open("w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_fieldnames)
        writer.writeheader()
        writer.writerows(merged_rows)
        stats["rows_written"] = len(merged_rows)

    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge multiple CSV files")
    parser.add_argument("inputs", nargs="+", type=Path, help="Input CSV files")
    parser.add_argument(
        "-o", "--output", type=Path, required=True, help="Output CSV file"
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["rows", "columns"],
        default="rows",
        help="Merge mode: rows (append) or columns (join)",
    )
    parser.add_argument("--source", action="store_true", help="Add source file column")
    parser.add_argument("--dedup", action="store_true", help="Remove duplicate rows")
    parser.add_argument(
        "--encoding", default="utf-8", help="File encoding (default: utf-8)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show stats without writing file"
    )

    args = parser.parse_args(argv)

    try:
        stats = merge_csv_files(
            args.inputs,
            args.output,
            args.mode,
            args.source,
            args.dedup,
            args.encoding,
        )

        print(f"Files processed: {stats['files_processed']}")
        print(f"Total rows read: {stats['rows_total']}")
        print(f"Rows written: {stats['rows_written']}")
        if stats["duplicates_removed"] > 0:
            print(f"Duplicates removed: {stats['duplicates_removed']}")

        if not args.dry_run:
            print(f"Output saved to: {args.output}")
        else:
            print("(Dry run - no file written)")

        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
