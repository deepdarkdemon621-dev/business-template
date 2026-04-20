from __future__ import annotations

import typer

from app.cli_commands import rbac as rbac_cmd

app = typer.Typer(no_args_is_help=True)
app.add_typer(rbac_cmd.app, name="rbac")


if __name__ == "__main__":
    app()
