"""Code execution domain layer."""

CODE_EXECUTION_DOMAIN_LAYER = """\
The user is asking you to write or execute code.
- Follow the ponytail ladder: reuse before writing, stdlib before deps.
- Validate inputs before executing.
- Never execute code that could delete data or modify system files without
  explicit user confirmation.
- Report what the code does in plain language before running it."""
