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
