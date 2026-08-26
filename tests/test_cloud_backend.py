"""
Unit and integration tests for AURA Cloud Backend:
- Secure PBKDF2 password hashing & verification
- User registration, login, and sessions
- Pairing code lifecycle and single-use validation
- Multi-tenant device isolation (Tenant A cannot see Tenant B's devices)
- Telemetry Relay subscriber isolation
"""

from __future__ import annotations

from pathlib import Path
import pytest

from aura.cloud.security import hash_password, verify_password, generate_pairing_code
from aura.cloud.storage import CloudStorage
from aura.cloud.relay import CloudTelemetryRelay


@pytest.fixture
def cloud_storage(tmp_path: Path) -> CloudStorage:
    db_path = tmp_path / "test_cloud.db"
    return CloudStorage(db_path)


def test_password_hashing_and_verification() -> None:
    pw = "SuperSecretP@ssw0rd!123"
    pw_hash = hash_password(pw)
    assert pw_hash.startswith("pbkdf2_sha256$100000$")
    assert verify_password(pw, pw_hash) is True
    assert verify_password("WrongPassword", pw_hash) is False
    assert verify_password("", pw_hash) is False


def test_cloud_user_and_session_lifecycle(cloud_storage: CloudStorage) -> None:
    # 1. Create User
    pw_hash = hash_password("Password123")
    user = cloud_storage.create_user("usr_001", "alice@example.com", pw_hash, "Alice Security")
    assert user["user_id"] == "usr_001"
    assert user["email"] == "alice@example.com"

    # 2. Duplicate email rejection
    with pytest.raises(Exception):
        cloud_storage.create_user("usr_002", "alice@example.com", pw_hash, "Alice Duplicate")

    # 3. Create & Validate Session
    token = cloud_storage.create_session("usr_001", ttl_hours=24.0)
    assert token.startswith("aura_usr_")
    session = cloud_storage.validate_session(token)
    assert session is not None
    assert session["user_id"] == "usr_001"
    assert session["email"] == "alice@example.com"

    # 4. Revoke Session
    assert cloud_storage.revoke_session(token) is True
    assert cloud_storage.validate_session(token) is None


def test_cloud_pairing_code_and_device_consumption(cloud_storage: CloudStorage) -> None:
    pw_hash = hash_password("Password123")
    cloud_storage.create_user("usr_bob", "bob@example.com", pw_hash, "Bob")

    # 1. Create pairing code
    code = cloud_storage.create_pairing_session("usr_bob", "Bob Laptop", ttl_seconds=600)
    assert len(code) >= 8

    # 2. Consume pairing code from agent
    device_id, device_token, user_id = cloud_storage.consume_pairing_code(
        pairing_code=code,
        hostname="BOB-WIN11",
        os_version="Windows 11 Pro",
    )
    assert device_id.startswith("dev_")
    assert device_token.startswith("aura_dev_")
    assert user_id == "usr_bob"

    # 3. Single-use enforcement: second consumption MUST fail
    with pytest.raises(ValueError, match="already consumed"):
        cloud_storage.consume_pairing_code(code, "ATTACKER-PC")

    # 4. Device queries
    device = cloud_storage.get_device_by_id(device_id)
    assert device is not None
    assert device["device_name"] == "Bob Laptop"
    assert device["hostname"] == "BOB-WIN11"

    token_lookup = cloud_storage.get_device_by_token(device_token)
    assert token_lookup is not None
    assert token_lookup["device_id"] == device_id


def test_multi_tenant_device_isolation(cloud_storage: CloudStorage) -> None:
    """Verify Tenant A cannot see or manage Tenant B's devices."""
    pw_hash = hash_password("Password123")
    cloud_storage.create_user("usr_a", "tenant_a@example.com", pw_hash, "Tenant A")
    cloud_storage.create_user("usr_b", "tenant_b@example.com", pw_hash, "Tenant B")

    code_a = cloud_storage.create_pairing_session("usr_a", "Device A")
    code_b = cloud_storage.create_pairing_session("usr_b", "Device B")

    dev_a_id, _, _ = cloud_storage.consume_pairing_code(code_a, "PC-A")
    dev_b_id, _, _ = cloud_storage.consume_pairing_code(code_b, "PC-B")

    # Tenant A devices
    devices_a = cloud_storage.get_user_devices("usr_a")
    assert len(devices_a) == 1
    assert devices_a[0]["device_id"] == dev_a_id

    # Tenant B devices
    devices_b = cloud_storage.get_user_devices("usr_b")
    assert len(devices_b) == 1
    assert devices_b[0]["device_id"] == dev_b_id

    # Tenant A cannot delete Tenant B's device
    assert cloud_storage.delete_device(user_id="usr_a", device_id=dev_b_id) is False
    # Tenant B device still exists
    assert cloud_storage.get_device_by_id(dev_b_id) is not None
