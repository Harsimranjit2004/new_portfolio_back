import secrets

from fastapi import APIRouter, HTTPException, status

from ..config import get_settings
from ..schemas import AdminLoginRequest, AdminLoginResponse
from ..services.auth_service import SESSION_TTL_SECONDS, create_session_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AdminLoginResponse)
def login(payload: AdminLoginRequest):
    settings = get_settings()
    valid_username = secrets.compare_digest(payload.username, settings.admin_username)
    valid_password = bool(settings.admin_password_hash) and verify_password(payload.password, settings.admin_password_hash)
    if not (valid_username and valid_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    token = create_session_token(settings.admin_api_key, payload.username)
    return AdminLoginResponse(token=token, expires_in=SESSION_TTL_SECONDS)
