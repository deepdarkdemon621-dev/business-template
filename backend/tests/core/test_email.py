import logging
from unittest.mock import patch

import pytest

from app.core.email import send_email


@pytest.mark.asyncio
async def test_send_email_dev_fallback_logs(caplog):
    """When SMTP_HOST is empty, email body is logged instead of sent."""
    import app.core.email as email_module

    with patch.object(email_module._settings, "smtp_host", ""):
        with caplog.at_level(logging.INFO, logger="app.core.email"):
            await send_email(
                to="user@example.com",
                subject="Reset your password",
                template="password_reset",
                context={"reset_link": "http://localhost/reset?token=abc", "ttl_hours": 1},
            )
    assert "user@example.com" in caplog.text
    assert "http://localhost/reset?token=abc" in caplog.text
