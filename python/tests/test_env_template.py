import pytest
from pathlib import Path
from scripts.env_template import generate_template, is_sensitive_key, main


class TestEnvTemplate:
    def test_is_sensitive_key_default_patterns(self):
        assert is_sensitive_key("API_KEY") is True
        assert is_sensitive_key("password") is True
        assert is_sensitive_key("SECRET_TOKEN") is True
        assert is_sensitive_key("AUTH_HEADER") is True
        assert is_sensitive_key("CREDENTIALS_FILE") is True
        assert is_sensitive_key("PRIVATE_KEY") is True

    def test_is_sensitive_key_non_sensitive(self):
        assert is_sensitive_key("DATABASE_URL") is False
        assert is_sensitive_key("PORT") is False
        assert is_sensitive_key("DEBUG") is False
        assert is_sensitive_key("HOSTNAME") is False

    def test_is_sensitive_key_custom_patterns(self):
        patterns = [r".*custom.*"]
        assert is_sensitive_key("MY_CUSTOM_VAR", patterns) is True
        assert is_sensitive_key("API_KEY", patterns) is False

    def test_generate_template_masks_sensitive_values(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "DATABASE_URL=postgres://localhost/db\n"
            "API_KEY=secret123\n"
            "PORT=8080\n"
            "PASSWORD=mypassword\n"
        )

        template = generate_template(env_file)

        assert "DATABASE_URL=postgres://localhost/db" in template
        assert "API_KEY=YOUR_VALUE_HERE" in template
        assert "PORT=8080" in template
        assert "PASSWORD=YOUR_VALUE_HERE" in template

    def test_generate_template_custom_placeholder(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret123\n")

        template = generate_template(env_file, placeholder="FILL_ME_IN")

        assert "API_KEY=FILL_ME_IN" in template

    def test_generate_template_keeps_comments(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# This is a comment\n"
            "DATABASE_URL=postgres://localhost/db\n"
            "\n"
            "# Another comment\n"
            "PORT=8080\n"
        )

        template = generate_template(env_file)

        assert "# This is a comment" in template
        assert "# Another comment" in template

    def test_generate_template_writes_to_file(self, tmp_path):
        env_file = tmp_path / ".env"
        output_file = tmp_path / ".env.template"
        env_file.write_text("API_KEY=secret123\n")

        generate_template(env_file, output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "API_KEY=YOUR_VALUE_HERE" in content

    def test_generate_template_keep_values(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret123\n")

        template = generate_template(env_file, keep_values=True)

        assert "API_KEY=secret123" in template

    def test_generate_template_file_not_found(self, tmp_path):
        env_file = tmp_path / "nonexistent.env"

        with pytest.raises(FileNotFoundError):
            generate_template(env_file)

    def test_generate_template_handles_quotes(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "DATABASE_URL=\"postgres://localhost/db\"\nAPI_KEY='secret123'\n"
        )

        template = generate_template(env_file)

        assert "DATABASE_URL=postgres://localhost/db" in template
        assert "API_KEY=YOUR_VALUE_HERE" in template


class TestEnvTemplateCLI:
    def test_cli_basic(self, tmp_path, capsys):
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret123\n")
        output_file = tmp_path / ".env.template"

        result = main([str(env_file), "-o", str(output_file)])

        assert result == 0
        assert output_file.exists()

    def test_cli_dry_run(self, tmp_path, capsys):
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret123\n")

        result = main([str(env_file), "--dry-run"])
        captured = capsys.readouterr()

        assert result == 0
        assert "API_KEY=YOUR_VALUE_HERE" in captured.out

    def test_cli_file_not_found(self, capsys):
        result = main(["nonexistent.env"])
        captured = capsys.readouterr()

        assert result == 1
        assert "not found" in captured.err.lower()

    def test_cli_custom_placeholder(self, tmp_path, capsys):
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret123\n")

        result = main([str(env_file), "--dry-run", "-p", "FILL_ME_IN"])
        captured = capsys.readouterr()

        assert result == 0
        assert "API_KEY=FILL_ME_IN" in captured.out

    def test_cli_keep_values(self, tmp_path, capsys):
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret123\n")

        result = main([str(env_file), "--dry-run", "--keep-values"])
        captured = capsys.readouterr()

        assert result == 0
        assert "API_KEY=secret123" in captured.out
