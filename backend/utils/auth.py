"""
Authentication utilities
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
import httpx

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from database import db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Get current user from JWT token or Emergent OAuth session token.
    Supports both email/password JWT and Google OAuth session tokens.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # First, try to decode as JWT (for email/password login)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
        
        # The sub field contains email for JWT tokens
        user = await db.users.find_one({"email": sub})
        if user is None:
            user = await db.users.find_one({"user_id": sub})
        if user is None:
            user = await db.users.find_one({"_id": sub})
        if user is None:
            raise credentials_exception
        return user
    except JWTError:
        pass  # Not a valid JWT, try session token lookup
    
    # Second, try as Emergent OAuth session token
    try:
        session = await db.user_sessions.find_one({"session_token": token})
        if session:
            user = await db.users.find_one({"email": session["email"]})
            if user:
                return user
        
        # Try to validate with Emergent OAuth API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.emergentagent.com/oauth/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                oauth_data = response.json()
                user = await db.users.find_one({"email": oauth_data["email"]})
                
                if user:
                    await db.user_sessions.update_one(
                        {"email": oauth_data["email"]},
                        {
                            "$set": {
                                "session_token": token,
                                "updated_at": datetime.now(timezone.utc)
                            }
                        },
                        upsert=True
                    )
                    return user
    except Exception:
        pass
    
    raise credentials_exception
