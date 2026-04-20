from __future__ import annotations

import typer

app = typer.Typer(no_args_is_help=True)


@app.command("list-roles")
def list_roles() -> None:
    """List all roles and their permission grants."""
    typer.echo("(stub — filled in G5)")
