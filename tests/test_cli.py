from click.testing import CliRunner

from tools import cli
from tools.client import Client


def test_cli_health(monkeypatch):
    called = {}

    def fake_get(self, path, **kwargs):
        called["path"] = path
        return {"status": "ok"}

    monkeypatch.setattr(Client, "get", fake_get)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["health", "--url", "http://example"])
    assert result.exit_code == 0
    assert "status" in result.output
    assert called["path"] == "/health"


def test_cli_db_migrate(monkeypatch):
    class _Done:
        returncode = 0

    def fake_run(cmd, check):
        assert cmd[:2] == ["alembic", "upgrade"]
        return _Done()

    monkeypatch.setattr("subprocess.run", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["db", "migrate"])
    assert result.exit_code == 0


def test_cli_db_rollback(monkeypatch):
    invoked = {}

    class _Done:
        returncode = 0

    def fake_run(cmd, check):
        invoked["cmd"] = cmd
        return _Done()

    monkeypatch.setattr("subprocess.run", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["db", "rollback"])
    assert result.exit_code == 0
    assert invoked["cmd"] == ["alembic", "downgrade", "-1"]


def test_cli_db_status(monkeypatch):
    class _Done:
        returncode = 0

    def fake_run(cmd, check):
        assert cmd == ["alembic", "current"]
        return _Done()

    monkeypatch.setattr("subprocess.run", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["db", "status"])
    assert result.exit_code == 0


def test_cli_jwt_generate(monkeypatch):
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError:
        import pytest

        pytest.skip("cryptography not installed")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    env_pem = pem.replace("\n", "\\n")

    monkeypatch.setenv("JWT_PRIVATE_KEY", env_pem)
    monkeypatch.setenv("JWT_ALGORITHM", "RS256")

    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        ["jwt", "generate", "--tenant-id", "00000000-0000-0000-0000-000000000001"],
    )
    assert result.exit_code == 0, result.output
    # Token is three base64url segments separated by dots
    token = result.output.strip().splitlines()[0]
    assert token.count(".") == 2


def test_cli_jwt_generate_missing_key(monkeypatch):
    monkeypatch.delenv("JWT_PRIVATE_KEY", raising=False)
    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        ["jwt", "generate", "--tenant-id", "00000000-0000-0000-0000-000000000001"],
    )
    assert result.exit_code != 0
