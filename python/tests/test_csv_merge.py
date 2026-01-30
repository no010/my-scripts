import pytest
from pathlib import Path
from scripts.csv_merge import merge_csv_files, main


class TestCSVMerge:
    def test_merge_by_rows_basic(self, tmp_path):
        csv1 = tmp_path / "file1.csv"
        csv2 = tmp_path / "file2.csv"
        output = tmp_path / "output.csv"

        csv1.write_text("name,age\nAlice,30\nBob,25\n")
        csv2.write_text("name,age\nCharlie,35\nDavid,28\n")

        stats = merge_csv_files([csv1, csv2], output, merge_mode="rows")

        assert stats["files_processed"] == 2
        assert stats["rows_total"] == 4
        assert stats["rows_written"] == 4

        content = output.read_text()
        assert "Alice,30" in content
        assert "Bob,25" in content
        assert "Charlie,35" in content
        assert "David,28" in content

    def test_merge_by_rows_with_source(self, tmp_path):
        csv1 = tmp_path / "file1.csv"
        csv2 = tmp_path / "file2.csv"
        output = tmp_path / "output.csv"

        csv1.write_text("name,age\nAlice,30\n")
        csv2.write_text("name,age\nBob,25\n")

        stats = merge_csv_files(
            [csv1, csv2], output, merge_mode="rows", add_source=True
        )

        content = output.read_text()
        assert "_source_file" in content
        assert "file1.csv" in content
        assert "file2.csv" in content

    def test_merge_by_rows_deduplicate(self, tmp_path):
        csv1 = tmp_path / "file1.csv"
        csv2 = tmp_path / "file2.csv"
        output = tmp_path / "output.csv"

        csv1.write_text("name,age\nAlice,30\n")
        csv2.write_text("name,age\nAlice,30\nBob,25\n")

        stats = merge_csv_files(
            [csv1, csv2], output, merge_mode="rows", deduplicate=True
        )

        assert stats["rows_total"] == 3
        assert stats["rows_written"] == 2
        assert stats["duplicates_removed"] == 1

    def test_merge_by_columns_basic(self, tmp_path):
        csv1 = tmp_path / "users.csv"
        csv2 = tmp_path / "details.csv"
        output = tmp_path / "output.csv"

        csv1.write_text("id,name\n1,Alice\n2,Bob\n")
        csv2.write_text("age,city\n30,NYC\n25,LA\n")

        stats = merge_csv_files([csv1, csv2], output, merge_mode="columns")

        assert stats["files_processed"] == 2
        assert stats["rows_written"] == 2

        content = output.read_text()
        assert "users.id" in content or "id" in content
        assert "users.name" in content or "name" in content
        assert "details.age" in content or "age" in content
        assert "details.city" in content or "city" in content

    def test_merge_by_columns_row_count_mismatch(self, tmp_path):
        csv1 = tmp_path / "file1.csv"
        csv2 = tmp_path / "file2.csv"
        output = tmp_path / "output.csv"

        csv1.write_text("id\n1\n2\n")
        csv2.write_text("value\na\n")

        with pytest.raises(ValueError, match="Row count mismatch"):
            merge_csv_files([csv1, csv2], output, merge_mode="columns")

    def test_merge_no_input_files(self, tmp_path):
        output = tmp_path / "output.csv"

        with pytest.raises(ValueError, match="No input files"):
            merge_csv_files([], output)

    def test_merge_file_not_found(self, tmp_path):
        csv1 = tmp_path / "file1.csv"
        output = tmp_path / "output.csv"

        with pytest.raises(FileNotFoundError):
            merge_csv_files([csv1], output)

    def test_merge_different_encodings(self, tmp_path):
        csv1 = tmp_path / "file1.csv"
        output = tmp_path / "output.csv"

        csv1.write_text("name\n测试\n", encoding="utf-8")

        stats = merge_csv_files([csv1], output, encoding="utf-8")

        assert stats["files_processed"] == 1


class TestCSVMergeCLI:
    def test_cli_merge_rows(self, tmp_path, capsys):
        csv1 = tmp_path / "file1.csv"
        csv2 = tmp_path / "file2.csv"
        output = tmp_path / "output.csv"

        csv1.write_text("name,age\nAlice,30\n")
        csv2.write_text("name,age\nBob,25\n")

        result = main([str(csv1), str(csv2), "-o", str(output)])

        assert result == 0
        assert output.exists()

    def test_cli_merge_columns(self, tmp_path, capsys):
        csv1 = tmp_path / "file1.csv"
        csv2 = tmp_path / "file2.csv"
        output = tmp_path / "output.csv"

        csv1.write_text("id\n1\n")
        csv2.write_text("value\na\n")

        result = main([str(csv1), str(csv2), "-o", str(output), "-m", "columns"])

        assert result == 0

    def test_cli_with_source(self, tmp_path):
        csv1 = tmp_path / "file1.csv"
        csv2 = tmp_path / "file2.csv"
        output = tmp_path / "output.csv"

        csv1.write_text("name\nAlice\n")
        csv2.write_text("name\nBob\n")

        result = main([str(csv1), str(csv2), "-o", str(output), "--source"])

        assert result == 0
        content = output.read_text()
        assert "_source_file" in content

    def test_cli_dry_run(self, tmp_path, capsys):
        csv1 = tmp_path / "file1.csv"
        csv2 = tmp_path / "file2.csv"
        output = tmp_path / "output.csv"

        csv1.write_text("name\nAlice\n")
        csv2.write_text("name\nBob\n")

        result = main([str(csv1), str(csv2), "-o", str(output), "--dry-run"])
        captured = capsys.readouterr()

        assert result == 0
        assert "Files processed" in captured.out
        assert not output.exists()

    def test_cli_error_file_not_found(self, capsys):
        result = main(["nonexistent.csv", "-o", "output.csv"])

        assert result == 1
