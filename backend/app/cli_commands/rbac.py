from __future__ import annotations

import typer

app = typer.Typer(no_args_is_help=True)


@app.command("list-roles")
def list_roles() -> None:
    """List all roles and their permission grants."""
    typer.echo("(stub — filled in G5)")


@app.command("grant-role")
def grant_role(email: str, role_code: str) -> None:
    """Grant `role_code` to user identified by `email`. Idempotent."""
    import asyncio

    from sqlalchemy import select

    from app.core.database import async_session
    from app.modules.auth.models import User
    from app.modules.rbac import crud

    async def _run() -> None:
        async with async_session() as db:
            user = (
                await db.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if user is None:
                typer.echo(f"User not found: {email}", err=True)
                raise typer.Exit(code=1)
            role = await crud.get_role_by_code(db, role_code)
            if role is None:
                typer.echo(f"Role not found: {role_code}", err=True)
                raise typer.Exit(code=1)
            inserted = await crud.grant_role(db, user.id, role.id)
            await db.commit()
            typer.echo("granted" if inserted else "already granted")

    asyncio.run(_run())


@app.command("revoke-role")
def revoke_role(email: str, role_code: str) -> None:
    """Revoke `role_code` from user. Idempotent."""
    import asyncio

    from sqlalchemy import select

    from app.core.database import async_session
    from app.modules.auth.models import User
    from app.modules.rbac import crud

    async def _run() -> None:
        async with async_session() as db:
            user = (
                await db.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if user is None:
                typer.echo(f"User not found: {email}", err=True)
                raise typer.Exit(code=1)
            role = await crud.get_role_by_code(db, role_code)
            if role is None:
                typer.echo(f"Role not found: {role_code}", err=True)
                raise typer.Exit(code=1)
            removed = await crud.revoke_role(db, user.id, role.id)
            await db.commit()
            typer.echo("revoked" if removed else "not granted (noop)")

    asyncio.run(_run())


@app.command("list-user")
def list_user(email: str) -> None:
    """Show roles and effective permissions for a user."""
    import asyncio

    from sqlalchemy import select

    from app.core.database import async_session
    from app.core.permissions import SUPERADMIN_ALL, get_user_permissions
    from app.modules.auth.models import User
    from app.modules.rbac.models import Role, UserRole

    async def _run() -> None:
        async with async_session() as db:
            user = (
                await db.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if user is None:
                typer.echo(f"User not found: {email}", err=True)
                raise typer.Exit(code=1)
            roles_q = await db.execute(
                select(Role).join(UserRole).where(UserRole.user_id == user.id)
            )
            roles = [r.code for r in roles_q.scalars().all()]
            typer.echo(f"Email: {email}")
            typer.echo(f"Roles: {', '.join(roles) if roles else '(none)'}")
            perms = await get_user_permissions(db, user)
            if perms is SUPERADMIN_ALL:
                typer.echo("Permissions: (superadmin — all)")
            else:
                assert isinstance(perms, dict)
                for code, scope in sorted(perms.items()):
                    typer.echo(f"  {code} @ {scope.value}")

    asyncio.run(_run())
