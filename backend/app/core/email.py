from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
_template_dir = Path(__file__).resolve().parent.parent.parent / "templates" / "email"
_jinja_env = Environment(loader=FileSystemLoader(str(_template_dir)), autoescape=True)


async def send_email(
    to: str,
    subject: str,
    template: str,
    context: dict,
) -> None:
    html = _jinja_env.get_template(f"{template}.html").render(**context)

    if not _settings.smtp_host:
        logger.info("DEV EMAIL to=%s subject=%s\n%s", to, subject, html)
        return

    import aiosmtplib

    await aiosmtplib.send(
        html,
        sender=_settings.smtp_from or "noreply@example.com",
        recipients=[to],
        hostname=_settings.smtp_host,
        port=_settings.smtp_port,
        username=_settings.smtp_user or None,
        password=_settings.smtp_password or None,
    )
