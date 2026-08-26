"""
FastAPI REST and WebSocket route handlers for AURA Cloud Backend.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import re
from typing import Any
import uuid

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field, field_validator

from aura.cloud.security import hash_password, verify_password
from aura.cloud.storage import CloudStorage
from aura.cloud.relay import CloudTelemetryRelay

logger = logging.getLogger(__name__)

cloud_router = APIRouter(prefix="/api/v1")

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_cloud_storage(request: Request) -> CloudStorage:
    return request.app.state.cloud_storage


def get_telemetry_relay(request: Request) -> CloudTelemetryRelay:
    return request.app.state.telemetry_relay


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    storage: CloudStorage = Depends(get_cloud_storage),
) -> dict[str, Any]:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(status_code=401, detail="Authentication token required.")

    session_info = storage.validate_session(token)
    if not session_info:
        raise HTTPException(status_code=401, detail="Session expired or invalid.")

    return session_info


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)
    display_name: str = Field(min_length=1, default="Security Officer")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format.")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format.")
        return v


class AuthResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    token: str


class DeviceResponse(BaseModel):
    device_id: str
    device_name: str
    platform: str
    os_version: str | None = None
    hostname: str | None = None
    is_online: bool
    last_heartbeat: str | None = None
    created_at: str


class CreatePairingRequest(BaseModel):
    device_name: str = "Windows PC"


class PairingResponse(BaseModel):
    pairing_code: str
    expires_in_seconds: int
    instructions: str


class CompletePairingRequest(BaseModel):
    pairing_code: str
    hostname: str
    os_version: str = "Windows"


class PairAgentResponse(BaseModel):
    device_id: str
    device_token: str
    status: str = "PAIRED"


@cloud_router.post("/auth/register", response_model=AuthResponse)
async def register(body: RegisterRequest, storage: CloudStorage = Depends(get_cloud_storage)):
    existing = storage.get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    pw_hash = hash_password(body.password)
    user = storage.create_user(user_id, body.email, pw_hash, body.display_name)
    token = storage.create_session(user_id)

    return AuthResponse(
        user_id=user["user_id"],
        email=user["email"],
        display_name=user["display_name"],
        token=token,
    )


@cloud_router.post("/auth/login", response_model=AuthResponse)
async def login(body: LoginRequest, storage: CloudStorage = Depends(get_cloud_storage)):
    user = storage.get_user_by_email(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = storage.create_session(user["user_id"])
    return AuthResponse(
        user_id=user["user_id"],
        email=user["email"],
        display_name=user["display_name"],
        token=token,
    )


@cloud_router.post("/auth/logout")
async def logout(
    authorization: str | None = Header(default=None),
    storage: CloudStorage = Depends(get_cloud_storage),
):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        storage.revoke_session(token)
    return {"status": "SUCCESS", "message": "Signed out cleanly."}


@cloud_router.get("/auth/me")
async def get_me(user: dict[str, Any] = Depends(get_current_user)):
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "display_name": user["display_name"],
    }


@cloud_router.get("/devices", response_model=list[DeviceResponse])
async def list_devices(
    user: dict[str, Any] = Depends(get_current_user),
    storage: CloudStorage = Depends(get_cloud_storage),
    relay: CloudTelemetryRelay = Depends(get_telemetry_relay),
):
    devices = storage.get_user_devices(user["user_id"])
    for dev in devices:
        is_live = relay.is_agent_connected(dev["device_id"])
        dev["is_online"] = is_live
    return devices


@cloud_router.post("/devices/pairing", response_model=PairingResponse)
async def create_pairing(
    body: CreatePairingRequest,
    user: dict[str, Any] = Depends(get_current_user),
    storage: CloudStorage = Depends(get_cloud_storage),
):
    code = storage.create_pairing_session(user["user_id"], body.device_name, ttl_seconds=600)
    return PairingResponse(
        pairing_code=code,
        expires_in_seconds=600,
        instructions="Run 'aura pair " + code + "' on your Windows device to pair it securely.",
    )


@cloud_router.post("/devices/pair", response_model=PairAgentResponse)
async def complete_agent_pairing(
    body: CompletePairingRequest,
    storage: CloudStorage = Depends(get_cloud_storage),
):
    try:
        device_id, device_token, user_id = storage.consume_pairing_code(
            pairing_code=body.pairing_code,
            hostname=body.hostname,
            os_version=body.os_version,
        )
        return PairAgentResponse(device_id=device_id, device_token=device_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@cloud_router.post("/devices/{device_id}/revoke")
async def revoke_device(
    device_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    storage: CloudStorage = Depends(get_cloud_storage),
):
    ok = storage.revoke_device(user["user_id"], device_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Device not found or not owned by user.")
    return {"status": "SUCCESS", "message": f"Device {device_id} revoked."}


@cloud_router.delete("/devices/{device_id}")
async def delete_device(
    device_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    storage: CloudStorage = Depends(get_cloud_storage),
):
    ok = storage.delete_device(user["user_id"], device_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Device not found or not owned by user.")
    return {"status": "SUCCESS", "message": f"Device {device_id} removed."}


@cloud_router.get("/health")
async def cloud_health():
    return {
        "status": "HEALTHY",
        "service": "AURA Cloud API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "PRODUCTION_CLOUD",
    }


@cloud_router.websocket("/stream/agent")
async def agent_stream_endpoint(
    websocket: WebSocket,
    device_token: str | None = Query(default=None),
):
    storage: CloudStorage = websocket.app.state.cloud_storage
    relay: CloudTelemetryRelay = websocket.app.state.telemetry_relay

    if not device_token:
        sec_protocol = websocket.headers.get("sec-websocket-protocol", "")
        if sec_protocol and sec_protocol.startswith("device."):
            device_token = sec_protocol.split(".", 1)[1].strip()

    if not device_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    device = storage.get_device_by_token(device_token)
    if not device:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    device_id = device["device_id"]
    await websocket.accept()
    storage.update_device_online_status(device_id, True)
    await relay.register_agent(device_id, websocket)

    try:
        while True:
            raw_text = await websocket.receive_text()
            await relay.broadcast_to_device_subscribers(device_id, raw_text)
            storage.update_device_online_status(device_id, True)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as exc:
        logger.debug("Agent socket error for [%s]: %s", device_id, exc)
    finally:
        storage.update_device_online_status(device_id, False)
        await relay.unregister_agent(device_id)


@cloud_router.websocket("/stream/client")
async def client_stream_endpoint(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    device_id: str | None = Query(default=None),
):
    storage: CloudStorage = websocket.app.state.cloud_storage
    relay: CloudTelemetryRelay = websocket.app.state.telemetry_relay

    if not token:
        sec_protocol = websocket.headers.get("sec-websocket-protocol", "")
        if sec_protocol and sec_protocol.startswith("bearer."):
            token = sec_protocol.split(".", 1)[1].strip()

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    session_info = storage.validate_session(token)
    if not session_info:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = session_info["user_id"]

    if not device_id:
        devices = storage.get_user_devices(user_id)
        if devices:
            device_id = devices[0]["device_id"]
        else:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="No devices paired")
            return

    device = storage.get_device_by_id(device_id)
    if not device or device["user_id"] != user_id or device["is_revoked"]:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Device not authorized")
        return

    await websocket.accept()
    await relay.register_client(device_id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as exc:
        logger.debug("Client socket error for [%s]: %s", device_id, exc)
    finally:
        await relay.unregister_client(device_id, websocket)
