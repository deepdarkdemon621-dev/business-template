from typer.testing import CliRunner

from app.cli import app


def test_grant_role_unknown_email_exits_1():
    runner = CliRunner()
    result = runner.invoke(app, ["rbac", "grant-role", "nobody@example.com", "admin"])
    assert result.exit_code == 1
    # Error message goes to stderr via `typer.echo(..., err=True)`.
    assert "not found" in result.stderr.lower()


def test_revoke_role_noop_when_not_granted():
    runner = CliRunner()
    result = runner.invoke(app, ["rbac", "revoke-role", "admin@example.com", "member"])
    # admin@example.com is superadmin, never had member granted
    assert result.exit_code == 0
    assert "not granted" in result.stdout.lower() or "noop" in result.stdout.lower()
