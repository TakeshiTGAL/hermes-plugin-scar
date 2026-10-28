"""The six secret shapes are removed before a preview is kept."""

from support import redact

SECRET_KEY = "sk-testscarpluginvalue"
SECRET_GH = "ghp_scarpluginfakevalue"
SECRET_PW = "hunter2xyz"
SECRET_URL = "pa55word"


def test_json_api_key_is_removed():
    text = '{"api_key": "' + SECRET_KEY + '"}'
    cleaned = redact.redact(text)
    assert SECRET_KEY not in cleaned
    assert "<redacted>" in cleaned or "redacted" in cleaned.lower()


def test_json_token_is_removed():
    text = '{"token": "' + SECRET_GH + '"}'
    assert SECRET_GH not in redact.redact(text)


def test_bearer_header_is_removed():
    text = "Authorization: Bearer " + SECRET_GH
    assert SECRET_GH not in redact.redact(text)


def test_env_assignment_is_removed():
    text = "GITHUB_TOKEN=" + SECRET_GH
    cleaned = redact.redact(text)
    assert SECRET_GH not in cleaned
    assert "GITHUB_TOKEN=<redacted>" in cleaned


def test_password_flag_with_a_space_is_removed():
    text = "--password " + SECRET_PW
    cleaned = redact.redact(text)
    assert SECRET_PW not in cleaned
    assert "--password <redacted>" in cleaned


def test_url_userinfo_is_removed():
    text = "postgres://user:" + SECRET_URL + "@db.example/app"
    cleaned = redact.redact(text)
    assert SECRET_URL not in cleaned
    assert "<redacted>" in cleaned or "***" in cleaned


def test_older_shapes_still_move():
    pem = "-----BEGIN TEST PRIVATE KEY-----\nabc\n-----END TEST PRIVATE KEY-----"
    assert "abc" not in redact.redact(pem)
    assert "sk-testscarpluginvalue" not in redact.redact("sk-testscarpluginvalue")
    assert "a" * 32 not in redact.redact("a" * 32)


def test_slack_github_pat_and_aws_key_shapes_are_removed():
    samples = {
        "xoxb-1234567890-abcdef": "xoxb-",
        "xoxp-1234567890-abcdef": "xoxp-",
        "ghp_scarpluginfakevalue": "ghp_",
        "github_pat_scarpluginfakevalue": "github_pat_",
        "sk-testscarpluginvalue": "sk-",
        "AKIAIOSFODNN7EXAMPLE": "AKIA",
    }
    for secret, prefix in samples.items():
        cleaned = redact.redact("rm -rf ./build " + secret)
        assert secret not in cleaned
        assert prefix not in cleaned
        assert "rm" in cleaned


def test_preview_is_capped():
    cleaned = redact.redact("rm -rf " + ("q" * 800))
    assert len(cleaned) <= 500
    assert cleaned.endswith("...")
