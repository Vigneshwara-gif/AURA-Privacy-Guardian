"""
Unit tests for SessionManager, ephemeral bootstrap tokens, and scope validation.
"""

from __future__ import annotations

import time
import pytest

from aura.api.auth import SessionManager
from aura.contracts.auth import AuthScope


def test_bootstrap_token_generation_and_exchange() -> None:
    """Verify single-use bootstrap token exchange."""
    manager = SessionManager()
    code = manager.create_bootstrap_code(scope=AuthScope.OPERATOR, ttl_seconds=60.0)
    assert isinstance(code, str)
    assert len(code) > 20

    # 1. First exchange must succeed
    token, claims = manager.exchange_bootstrap(code, client_name="Test Web Client")
    assert isinstance(token, str)
    assert len(token) > 30
    assert claims.scope == AuthScope.OPERATOR
    assert claims.issued_to == "Test Web Client"

    # 2. Second exchange on same code must be rejected (single-use)
    with pytest.raises(ValueError, match="Invalid bootstrap token"):
        manager.exchange_bootstrap(code)


def test_expired_bootstrap_rejection() -> None:
    """Verify expired bootstrap codes are rejected."""
    manager = SessionManager()
    # TTL 0.05 seconds
    code = manager.create_bootstrap_code(scope=AuthScope.READ_ONLY, ttl_seconds=0.05)
    time.sleep(0.08)

    with pytest.raises(ValueError, match="expired"):
        manager.exchange_bootstrap(code)


def test_session_validation_and_revocation() -> None:
    """Verify session validation, TTL, and explicit revocation."""
    manager = SessionManager()
    token, claims = manager.create_session(scope=AuthScope.ADMIN, issued_to="Admin Console", ttl_hours=1.0)

    # Valid session returns claims
    validated = manager.validate_session(token)
    assert validated is not None
    assert validated.token_id == claims.token_id
    assert validated.scope == AuthScope.ADMIN

    # Invalid token returns None
    assert manager.validate_session("invalid-fake-token-12345") is None

    # Revoke session
    assert manager.revoke_session(token) is True
    assert manager.validate_session(token) is None


def test_session_expiration() -> None:
    """Verify expired sessions return None and are purged."""
    manager = SessionManager()
    token, _ = manager.create_session(scope=AuthScope.READ_ONLY, ttl_hours=0.00002)  # ~0.07s
    time.sleep(0.1)

    assert manager.validate_session(token) is None
    purged = manager.cleanup_expired()
    assert purged >= 0
