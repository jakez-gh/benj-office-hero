from click.testing import CliRunner

from tools import cli
from tools.client import Client


def test_cli_health(monkeypatch, tmp_path):
    # simulate Client.get returning a predictable dict
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


def test_cli_migrate(monkeypatch):
    # simulate subprocess.run failure and success
    class Dummy:
        def __init__(self, returncode):
            self.returncode = returncode

    def fake_run(cmd, check):
        assert cmd[:2] == ["alembic", "upgrade"]
        return Dummy(returncode=0)

    monkeypatch.setattr("subprocess.run", fake_run)
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["migrate"])
    assert result.exit_code == 0
