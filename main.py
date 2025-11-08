import json
import logging
import os
import random
import time
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple

from livekit import api
from pydantic import BaseModel, Field, ValidationError, field_validator
from werkzeug.wrappers import Response

# Structured logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration via env vars / secrets
LIVEKIT_URL = os.environ.get("LIVEKIT_URL")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET")

# CORS
CORS_ALLOW_ORIGIN = os.getenv("CORS_ALLOW_ORIGIN", "*")
CORS_ALLOW_HEADERS = os.getenv("CORS_ALLOW_HEADERS", "Content-Type, X-User-Id")
CORS_ALLOW_METHODS = os.getenv("CORS_ALLOW_METHODS", "GET, OPTIONS")
CORS_MAX_AGE = os.getenv("CORS_MAX_AGE", "3600")

def _cors_headers() -> Dict[str, str]:
    return {
        "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
        "Access-Control-Allow-Methods": CORS_ALLOW_METHODS,
        "Access-Control-Allow-Headers": CORS_ALLOW_HEADERS,
        "Access-Control-Max-Age": CORS_MAX_AGE,
        "Content-Type": "application/json",
    }

def _json_response(payload: Dict[str, Any], status: int = 200) -> Response:
    return Response(
        json.dumps(payload),
        status=status,
        headers=_cors_headers(),
    )

class QueryParams(BaseModel):
    provider: str = Field(default="elevenlabs")
    voice_id: str = Field(default="EXAVITQu4vr4xnSDxMaL")
    session_id: Optional[str] = None
    market_location: Optional[str] = None
    new_conversation: bool = Field(default=False)

    @field_validator("new_conversation", mode="before")
    @classmethod
    def parse_bool_like(cls, v):
        if isinstance(v, bool):
            return v
        if v is None:
            return False
        return str(v).lower() in ("true", "1", "yes", "y")

class ConnectionDetails(BaseModel):
    serverUrl: str
    roomName: str
    participantName: str
    participantToken: str

def _validate_config() -> Optional[Tuple[str, int]]:
    if not LIVEKIT_URL:
        return ("LIVEKIT_URL is not configured", 500)
    if not LIVEKIT_API_KEY:
        return ("LIVEKIT_API_KEY is not configured", 500)
    if not LIVEKIT_API_SECRET:
        return ("LIVEKIT_API_SECRET is not configured", 500)
    return None

def _create_participant_token(identity: str, metadata: Dict[str, Any], room_name: str) -> str:
    token = (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name(identity)
        .with_metadata(json.dumps(metadata, separators=(",", ":")))
        .with_grants(
            api.VideoGrants(
                room=room_name,
                room_join=True,
                can_publish=True,
                can_publish_data=True,
                can_subscribe=True,
            )
        )
        .with_ttl(timedelta(minutes=5))
    )
    return token.to_jwt()

def connection_details(request) -> Response:
    # CORS preflight
    if request.method == "OPTIONS":
        return _json_response({}, status=204)

    # Config validation
    config_err = _validate_config()
    if config_err:
        msg, code = config_err
        logger.error("Configuration error: %s", msg)
        return _json_response({"detail": msg}, status=code)

    # Parse and validate query params
    try:
        qp = QueryParams(**(request.args.to_dict(flat=True) if request.args else {}))
    except ValidationError as ve:
        logger.warning("Validation error: %s", ve)
        return _json_response({"detail": "Invalid query parameters", "errors": json.loads(ve.json())}, status=400)

    # Identity: prefer authenticated header if provided
    unique_id = random.randint(1, 10_000)
    current_ts_ms = int(time.time() * 1000)
    room_name = f"voice_room_{unique_id}_{current_ts_ms}"
    participant_identity = request.headers.get("X-User-Id", f"user_{unique_id}")

    # Metadata for LiveKit client
    metadata = {
        "provider": qp.provider,
        "voiceId": qp.voice_id,
        "sessionId": qp.session_id,
        "userId": participant_identity,
        "newConversation": qp.new_conversation,
        "marketLocation": qp.market_location,
    }

    # Attach correlation id if present
    correlation_id = request.headers.get("X-Request-Id") or request.headers.get("X-Correlation-Id")
    log_ctx = {"roomName": room_name, "userId": participant_identity, "correlationId": correlation_id}
    logger.info("Voice connection request: %s", json.dumps({**metadata, **{k:v for k,v in log_ctx.items() if v}}))

    try:
        participant_token = _create_participant_token(
            identity=participant_identity,
            metadata=metadata,
            room_name=room_name,
        )
    except Exception as e:
        logger.exception("Failed to create participant token")
        return _json_response({"detail": "Failed to create participant token"}, status=500)

    payload = ConnectionDetails(
        serverUrl=LIVEKIT_URL,
        roomName=room_name,
        participantName=participant_identity,
        participantToken=participant_token,
    ).model_dump()

    logger.info("Created voice connection: %s", json.dumps({**log_ctx, "status": "ok"}))
    return _json_response(payload, status=200)