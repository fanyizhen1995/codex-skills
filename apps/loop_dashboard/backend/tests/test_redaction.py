from loop_dashboard.redaction import redact_text


def test_redacts_common_credentials_but_keeps_context() -> None:
    text = "\n".join(
        [
            "Authorization: Bearer abc.def.ghi",
            "github token ghp_1234567890abcdef",
            "token=plain-token",
            "password = hunter2",
            "secret: open-sesame",
            "api_key=sk-test-123",
            "plain line",
        ]
    )

    redacted = redact_text(text)

    assert "Authorization: Bearer [REDACTED]" in redacted
    assert "github token [REDACTED]" in redacted
    assert "token=[REDACTED]" in redacted
    assert "password = [REDACTED]" in redacted
    assert "secret: [REDACTED]" in redacted
    assert "api_key=[REDACTED]" in redacted
    assert "plain line" in redacted
    assert "hunter2" not in redacted
    assert "open-sesame" not in redacted
    assert "ghp_1234567890abcdef" not in redacted


def test_redacts_broader_authorization_and_key_spellings() -> None:
    text = "\n".join(
        [
            "Authorization: Basic abc123==",
            'Authorization: Custom "opaque credential"',
            "api key = sk-space",
            "api-key: sk-dash",
            '"apiKey": "sk-json"',
            "accessToken = access-secret",
            "clientSecret: client-secret",
            "password: quoted-password",
        ]
    )

    redacted = redact_text(text)

    assert "Authorization: [REDACTED]" in redacted
    assert "api key = [REDACTED]" in redacted
    assert "api-key: [REDACTED]" in redacted
    assert '"apiKey": "[REDACTED]"' in redacted
    assert "accessToken = [REDACTED]" in redacted
    assert "clientSecret: [REDACTED]" in redacted
    assert "password: [REDACTED]" in redacted
    for secret in (
        "abc123",
        "opaque credential",
        "sk-space",
        "sk-dash",
        "sk-json",
        "access-secret",
        "client-secret",
        "quoted-password",
    ):
        assert secret not in redacted
