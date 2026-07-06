"""Validation tests."""

import pytest

from keprix.security.validation import InputValidator, ValidationError


def test_rejects_null_bytes():
    validator = InputValidator()
    with pytest.raises(ValidationError):
        validator.validate_string("hello\x00world", "field")


def test_rejects_oversized_string():
    validator = InputValidator()
    with pytest.raises(ValidationError):
        validator.validate_string("x" * 70000, "field")


def test_path_traversal_rejected(tmp_path):
    validator = InputValidator()
    base = tmp_path / "safe"
    base.mkdir()
    with pytest.raises(ValidationError):
        validator.validate_path("../../etc/passwd", "path", str(base))


def test_shell_metacharacters_rejected():
    validator = InputValidator()
    with pytest.raises(ValidationError):
        validator.validate_command_arg("file; rm -rf /", "arg")


def test_valid_url():
    validator = InputValidator()
    assert validator.validate_url("https://example.com/path", "url") == "https://example.com/path"
