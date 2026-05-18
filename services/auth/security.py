from datetime import datetime, timedelta, timezone
import hashlib, secrets, os

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()

_JWT_SECRET  = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
_JWT_ALG     = os.getenv("JWT_ALGORITHM", "HS256")
_ACCESS_EXP  = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
_REFRESH_EXP = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> tuple[str, int]:
    expire = datetime.now(timezone.utc) + timedelta(minutes=_ACCESS_EXP)
    payload = {"sub": user_id, "email": email, "exp": expire, "type": "access"}
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALG), _ACCESS_EXP * 60


def create_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(64)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALG])
        if payload.get("type") != "access":
            raise JWTError("Wrong token type")
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    payload = decode_access_token(credentials.credentials)
    return payload["sub"]