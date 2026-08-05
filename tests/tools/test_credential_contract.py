"""Tool credential contract tests."""

from __future__ import annotations

from keprix.tools.credential_contract import CredentialRoute, ToolCredentialRegistry, credential, credential_registry


def test_credential_decorator_registers_function_and_docstring() -> None:
    credential_registry.clear()

    @credential(
        tool_name="stripe.create_payment",
        routes=[
            CredentialRoute(
                host="api.stripe.com",
                header="Authorization",
                scheme="Bearer",
                secret_ref="stripe-secret-key",
            )
        ],
    )
    def create_payment() -> dict[str, bool]:
        """Create payment."""
        return {"ok": True}

    record = credential_registry.get("stripe.create_payment")

    assert create_payment() == {"ok": True}
    assert record is not None
    assert record.routes[0].host == "api.stripe.com"
    assert "Credential requirements" in (create_payment.__doc__ or "")
    assert "stripe-secret-key" in (create_payment.__doc__ or "")


def test_registry_audit_log_writes_without_secret_value(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    registry = ToolCredentialRegistry()
    route = CredentialRoute(host="api.sendgrid.com", header="Authorization", scheme="Bearer", secret_ref="sendgrid-api-key")

    entry = registry.audit_log("sendgrid.send_email", route, "injected", path="/v3/mail/send", method="POST", response_status=202)

    assert entry["credential_ref"] == "sendgrid-api-key"
    assert "secret" not in str(entry).lower().replace("secret_ref", "")
