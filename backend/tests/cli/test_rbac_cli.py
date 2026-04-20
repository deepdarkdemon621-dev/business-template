from typer.testing import CliRunner

from app.cli import app


def test_grant_role_unknown_email_exits_1():
    runner = CliRunner()
    result = runner.invoke(app, ["rbac", "grant-role", "nobody@example.com", "admin"])
    assert result.exit_code == 1
    # Error message goes to stderr via `typer.echo(..., err=True)`.
    assert "not found" in result.stderr.lower()
