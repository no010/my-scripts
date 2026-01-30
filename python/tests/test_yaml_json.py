import pytest
from pathlib import Path
from scripts.yaml_json import (
    convert_yaml_to_json,
    convert_json_to_yaml,
    batch_convert,
    main,
)


class TestYAMLJSON:
    def test_convert_yaml_to_json(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        json_file = tmp_path / "test.json"

        yaml_content = """
name: John
age: 30
items:
  - a
  - b
nested:
  key: value
"""
        yaml_file.write_text(yaml_content)

        convert_yaml_to_json(yaml_file, json_file)

        import json

        data = json.loads(json_file.read_text())
        assert data["name"] == "John"
        assert data["age"] == 30
        assert data["items"] == ["a", "b"]
        assert data["nested"]["key"] == "value"

    def test_convert_json_to_yaml(self, tmp_path):
        json_file = tmp_path / "test.json"
        yaml_file = tmp_path / "test.yaml"

        data = {"name": "John", "age": 30, "items": ["a", "b"]}
        import json

        json_file.write_text(json.dumps(data))

        convert_json_to_yaml(json_file, yaml_file)

        yaml_content = yaml_file.read_text()
        assert "name: John" in yaml_content
        assert "age: 30" in yaml_content

    def test_batch_convert_yaml_to_json(self, tmp_path):
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        (input_dir / "file1.yaml").write_text("key1: value1\n")
        (input_dir / "file2.yml").write_text("key2: value2\n")

        stats = batch_convert(input_dir, output_dir, "yaml", "json")

        assert stats["processed"] == 2
        assert stats["failed"] == 0
        assert (output_dir / "file1.json").exists()
        assert (output_dir / "file2.json").exists()

    def test_batch_convert_json_to_yaml(self, tmp_path):
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        import json

        (input_dir / "file1.json").write_text(json.dumps({"key": "value"}))

        stats = batch_convert(input_dir, output_dir, "json", "yaml")

        assert stats["processed"] == 1
        assert (output_dir / "file1.yaml").exists()

    def test_batch_convert_with_errors(self, tmp_path):
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        (input_dir / "invalid.yaml").write_text("{invalid yaml: [}")

        stats = batch_convert(input_dir, output_dir, "yaml", "json")

        assert stats["processed"] == 0
        assert stats["failed"] == 1
        assert len(stats["errors"]) == 1


class TestYAMLJSONCLI:
    def test_cli_convert_yaml_to_json(self, tmp_path, capsys):
        yaml_file = tmp_path / "test.yaml"
        json_file = tmp_path / "test.json"

        yaml_file.write_text("name: John\n")

        result = main(["convert", str(yaml_file), str(json_file)])

        assert result == 0
        assert json_file.exists()

    def test_cli_convert_json_to_yaml(self, tmp_path, capsys):
        import json

        json_file = tmp_path / "test.json"
        yaml_file = tmp_path / "test.yaml"

        json_file.write_text(json.dumps({"name": "John"}))

        result = main(["convert", str(json_file), str(yaml_file)])

        assert result == 0

    def test_cli_batch_convert(self, tmp_path, capsys):
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        (input_dir / "file1.yaml").write_text("key: value\n")

        result = main(
            [
                "batch",
                str(input_dir),
                str(output_dir),
                "--from",
                "yaml",
                "--to",
                "json",
            ]
        )
        captured = capsys.readouterr()

        assert result == 0
        assert "Files processed" in captured.out

    def test_cli_unsupported_conversion(self, tmp_path, capsys):
        txt_file = tmp_path / "test.txt"
        json_file = tmp_path / "test.json"

        txt_file.write_text("content")

        result = main(["convert", str(txt_file), str(json_file)])

        assert result == 1

    def test_cli_no_command(self, capsys):
        result = main([])

        assert result == 1
