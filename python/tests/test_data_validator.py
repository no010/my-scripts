import pytest
from pathlib import Path
import json
from scripts.data_validator import (
    validate_csv,
    validate_json,
    parse_rules,
    ValidationRule,
    ValidationResult,
    validate_email,
    validate_url,
)


class TestValidators:
    def test_validate_email_valid(self):
        assert validate_email("test@example.com") is True
        assert validate_email("user.name@domain.co.uk") is True

    def test_validate_email_invalid(self):
        assert validate_email("invalid") is False
        assert validate_email("@example.com") is False
        assert validate_email("test@") is False

    def test_validate_url_valid(self):
        assert validate_url("http://example.com") is True
        assert validate_url("https://example.com/path") is True

    def test_validate_url_invalid(self):
        assert validate_url("not-a-url") is False
        assert validate_url("ftp://example.com") is False


class TestParseRules:
    def test_parse_simple_rule(self):
        rules = parse_rules(["name:required"])
        assert len(rules) == 1
        assert rules[0].field == "name"
        assert rules[0].required is True

    def test_parse_type_rule(self):
        rules = parse_rules(["age:type=int"])
        assert rules[0].type_ == "int"

    def test_parse_pattern_rule(self):
        rules = parse_rules(["email:pattern=^.*@.*\\..*$"])
        assert rules[0].pattern == "^.*@.*\\..*$"

    def test_parse_min_max_rule(self):
        rules = parse_rules(["score:min=0:max=100"])
        assert rules[0].min_value == 0.0
        assert rules[0].max_value == 100.0

    def test_parse_unique_rule(self):
        rules = parse_rules(["id:unique"])
        assert rules[0].unique is True

    def test_parse_complex_rule(self):
        rules = parse_rules(["email:required:type=email:unique"])
        assert rules[0].field == "email"
        assert rules[0].required is True
        assert rules[0].type_ == "email"
        assert rules[0].unique is True


class TestValidateCSV:
    def test_validate_csv_all_valid(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,age\nAlice,30\nBob,25\n")

        rules = [ValidationRule(field="name", required=True)]
        result = validate_csv(csv_file, rules)

        assert result.valid is True
        assert result.total_rows == 2
        assert result.valid_rows == 2
        assert result.invalid_rows == 0

    def test_validate_csv_required_field_missing(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,age\n,30\nBob,25\n")

        rules = [ValidationRule(field="name", required=True)]
        result = validate_csv(csv_file, rules)

        assert result.valid is False
        assert result.invalid_rows == 1
        assert len(result.errors) == 1

    def test_validate_csv_type_validation(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("age\n30\nnot-a-number\n")

        rules = [ValidationRule(field="age", type_="int")]
        result = validate_csv(csv_file, rules)

        assert result.valid is False
        assert result.invalid_rows == 1

    def test_validate_csv_email_validation(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("email\ntest@example.com\ninvalid\n")

        rules = [ValidationRule(field="email", type_="email")]
        result = validate_csv(csv_file, rules)

        assert result.valid is False
        assert result.invalid_rows == 1

    def test_validate_csv_pattern_validation(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("code\nABC123\nXYZ\n")

        rules = [ValidationRule(field="code", pattern=r"^[A-Z]{3}\d{3}$")]
        result = validate_csv(csv_file, rules)

        assert result.valid is False
        assert result.invalid_rows == 1

    def test_validate_csv_min_max_validation(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("score\n50\n150\n-10\n")

        rules = [ValidationRule(field="score", type_="int", min_value=0, max_value=100)]
        result = validate_csv(csv_file, rules)

        assert result.valid is False
        assert result.invalid_rows == 2

    def test_validate_csv_unique_validation(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("id\n1\n2\n1\n")

        rules = [ValidationRule(field="id", unique=True)]
        result = validate_csv(csv_file, rules)

        assert result.valid is False
        assert len(result.duplicates) == 1


class TestValidateJSON:
    def test_validate_json_all_valid(self, tmp_path):
        json_file = tmp_path / "test.json"
        data = [{"name": "Alice"}, {"name": "Bob"}]
        json_file.write_text(json.dumps(data))

        rules = [ValidationRule(field="name", required=True)]
        result = validate_json(json_file, rules)

        assert result.valid is True
        assert result.total_rows == 2

    def test_validate_json_not_array(self, tmp_path):
        json_file = tmp_path / "test.json"
        json_file.write_text('{"name": "Alice"}')

        rules = [ValidationRule(field="name")]
        with pytest.raises(ValueError, match="must be an array"):
            validate_json(json_file, rules)


class TestDataValidatorCLI:
    def test_cli_validate_csv(self, tmp_path, capsys):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,age\nAlice,30\n")

        result = main([str(csv_file), "-f", "csv", "-r", "name:required"])

        assert result == 0

    def test_cli_validate_json(self, tmp_path, capsys):
        json_file = tmp_path / "test.json"
        json_file.write_text('[{"name": "Alice"}]')

        result = main([str(json_file), "-f", "json", "-r", "name:required"])

        assert result == 0

    def test_cli_validation_failed(self, tmp_path, capsys):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name\n\n")

        result = main([str(csv_file), "-f", "csv", "-r", "name:required"])

        assert result == 1

    def test_cli_strict_mode(self, tmp_path, capsys):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("id\n1\n1\n")

        result = main([str(csv_file), "-f", "csv", "-r", "id:unique", "--strict"])

        assert result == 1

    def test_cli_output_report(self, tmp_path, capsys):
        csv_file = tmp_path / "test.csv"
        report_file = tmp_path / "report.json"
        csv_file.write_text("name\n\n")

        result = main(
            [
                str(csv_file),
                "-f",
                "csv",
                "-r",
                "name:required",
                "--output",
                str(report_file),
            ]
        )

        assert result == 1
        assert report_file.exists()

    def test_cli_file_not_found(self, capsys):
        result = main(["nonexistent.csv", "-f", "csv", "-r", "name:required"])

        assert result == 1

    def test_cli_auto_detect_format(self, tmp_path, capsys):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name\nAlice\n")

        result = main([str(csv_file), "-r", "name:required"])

        assert result == 0
