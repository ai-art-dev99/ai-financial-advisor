from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from config import settings

bearer_scheme = HTTPBearer()


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key if hasattr(settings, "jwt_secret_key") else "change-me-in-production",
            algorithms=["HS256"],
        )
        if payload.get("type") != "access":
            raise JWTError()
        return payload["sub"]
    except (JWTError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")


class Settings:
    jwt_secret_key: str = "change-me-in-production"


# Pull from env
import os
_jwt_secret = os.getenv("JWT_SECRET_KEY", "change-me-in-production")


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, _jwt_secret, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise JWTError()
        return payload["sub"]
    except (JWTError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
