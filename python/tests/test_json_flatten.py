import pytest
from pathlib import Path
import json
from scripts.json_flatten import flatten, unflatten, process_file, main


class TestJSONFlatten:
    def test_flatten_simple_object(self):
        data = {"name": "John", "age": 30}
        result = flatten(data)
        assert result == {"name": "John", "age": 30}

    def test_flatten_nested_object(self):
        data = {"user": {"name": "John", "age": 30}}
        result = flatten(data)
        assert result == {"user.name": "John", "user.age": 30}

    def test_flatten_deeply_nested(self):
        data = {"a": {"b": {"c": {"d": "value"}}}}
        result = flatten(data)
        assert result == {"a.b.c.d": "value"}

    def test_flatten_with_array(self):
        data = {"items": ["a", "b", "c"]}
        result = flatten(data)
        assert result == {"items.0": "a", "items.1": "b", "items.2": "c"}

    def test_flatten_mixed_nested(self):
        data = {
            "user": {
                "name": "John",
                "addresses": [
                    {"city": "NYC", "zip": "10001"},
                    {"city": "LA", "zip": "90001"},
                ],
            }
        }
        result = flatten(data)
        assert result["user.name"] == "John"
        assert result["user.addresses.0.city"] == "NYC"
        assert result["user.addresses.1.zip"] == "90001"

    def test_flatten_custom_separator(self):
        data = {"user": {"name": "John"}}
        result = flatten(data, separator="/")
        assert result == {"user/name": "John"}

    def test_flatten_max_depth(self):
        data = {"a": {"b": {"c": {"d": "value"}}}}
        result = flatten(data, max_depth=1)
        assert result == {"a.b": {"c": {"d": "value"}}}

    def test_unflatten_simple(self):
        data = {"user.name": "John", "user.age": 30}
        result = unflatten(data)
        assert result == {"user": {"name": "John", "age": 30}}

    def test_unflatten_with_array_indices(self):
        data = {"items.0": "a", "items.1": "b"}
        result = unflatten(data)
        assert result == {"items": ["a", "b"]}

    def test_unflatten_custom_separator(self):
        data = {"user/name": "John"}
        result = unflatten(data, separator="/")
        assert result == {"user": {"name": "John"}}

    def test_flatten_unflatten_roundtrip(self):
        original = {
            "user": {
                "name": "John",
                "age": 30,
                "addresses": [{"city": "NYC"}, {"city": "LA"}],
            }
        }
        flattened = flatten(original)
        restored = unflatten(flattened)
        assert restored == original


class TestJSONFlattenFile:
    def test_process_file_flatten(self, tmp_path):
        input_file = tmp_path / "input.json"
        output_file = tmp_path / "output.json"

        data = {"user": {"name": "John"}}
        input_file.write_text(json.dumps(data))

        result = process_file(input_file, output_file, mode="flatten")

        assert output_file.exists()
        output_data = json.loads(output_file.read_text())
        assert output_data == {"user.name": "John"}

    def test_process_file_unflatten(self, tmp_path):
        input_file = tmp_path / "input.json"
        output_file = tmp_path / "output.json"

        data = {"user.name": "John"}
        input_file.write_text(json.dumps(data))

        result = process_file(input_file, output_file, mode="unflatten")

        output_data = json.loads(output_file.read_text())
        assert output_data == {"user": {"name": "John"}}

    def test_process_file_not_dict_for_flatten(self, tmp_path):
        input_file = tmp_path / "input.json"
        input_file.write_text("[1, 2, 3]")

        with pytest.raises(ValueError, match="must be a JSON object"):
            process_file(input_file, None, mode="flatten")


class TestJSONFlattenCLI:
    def test_cli_flatten(self, tmp_path, capsys):
        input_file = tmp_path / "input.json"
        output_file = tmp_path / "output.json"

        data = {"user": {"name": "John"}}
        input_file.write_text(json.dumps(data))

        result = main([str(input_file), "-o", str(output_file), "-m", "flatten"])

        assert result == 0
        assert output_file.exists()

    def test_cli_unflatten(self, tmp_path, capsys):
        input_file = tmp_path / "input.json"
        output_file = tmp_path / "output.json"

        data = {"user.name": "John"}
        input_file.write_text(json.dumps(data))

        result = main([str(input_file), "-o", str(output_file), "-m", "unflatten"])

        assert result == 0

    def test_cli_dry_run(self, tmp_path, capsys):
        input_file = tmp_path / "input.json"

        data = {"user": {"name": "John"}}
        input_file.write_text(json.dumps(data))

        result = main([str(input_file), "-m", "flatten", "--dry-run"])
        captured = capsys.readouterr()

        assert result == 0
        assert "user.name" in captured.out

    def test_cli_file_not_found(self, capsys):
        result = main(["nonexistent.json", "-m", "flatten"])

        assert result == 1

    def test_cli_custom_separator(self, tmp_path, capsys):
        input_file = tmp_path / "input.json"

        data = {"user": {"name": "John"}}
        input_file.write_text(json.dumps(data))

        result = main([str(input_file), "-m", "flatten", "--dry-run", "-s", "/"])
        captured = capsys.readouterr()

        assert result == 0
        assert "user/name" in captured.out

    def test_cli_max_depth(self, tmp_path, capsys):
        input_file = tmp_path / "input.json"

        data = {"a": {"b": {"c": "value"}}}
        input_file.write_text(json.dumps(data))

        result = main([str(input_file), "-m", "flatten", "--dry-run", "-d", "1"])
        captured = capsys.readouterr()

        assert result == 0
        assert "a.b" in captured.out
