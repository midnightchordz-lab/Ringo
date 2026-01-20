"""
Authentication routes - handles user registration, login, and OAuth
"""
import uuid
import secrets
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends, Form
from pydantic import EmailStr
import httpx
import resend

import sys
sys.path.insert(0, '/app/backend')

from database import db
from config import RESEND_API_KEY, SENDER_EMAIL, FRONTEND_URL, SECRET_KEY, ALGORITHM
from models.schemas import UserRegister, UserLogin, Token, UserResponse

from passlib.context import CryptContext
from jose import jwt

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Initialize Resend
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def send_verification_email(email: str, token: str, name: str):
    """Send verification email using Resend"""
    if not RESEND_API_KEY:
        print(f"[DEV MODE] Verification link: {FRONTEND_URL}/verify-email?token={token}")
        return
    
    verification_link = f"{FRONTEND_URL}/verify-email?token={token}"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%); padding: 40px; text-align: center;">
            <h1 style="color: white; margin: 0;">Welcome to ContentFlow!</h1>
        </div>
        <div style="padding: 40px; background: #1a1a1a; color: #ffffff;">
            <h2 style="color: #BEF264;">Hi {name}! 👋</h2>
            <p style="color: #a1a1aa; line-height: 1.6;">
                Thanks for signing up! Please verify your email address to get started.
            </p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_link}" 
                   style="background: #BEF264; color: #000; padding: 15px 40px; 
                          text-decoration: none; border-radius: 30px; font-weight: bold;
                          display: inline-block;">
                    Verify Email Address
                </a>
            </div>
            <p style="color: #71717a; font-size: 14px;">
                If you didn't create an account, you can safely ignore this email.
            </p>
        </div>
    </div>
    """
    
    try:
        resend.Emails.send({
            "from": SENDER_EMAIL,
            "to": email,
            "subject": "Verify your ContentFlow account",
            "html": html_content
        })
    except Exception as e:
        print(f"Failed to send verification email: {e}")


@router.post("/google-oauth")
async def google_oauth_callback(session_id: str = Form(...)):
    """Process Google OAuth via Emergent Auth"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id},
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Invalid session ID")
            
            oauth_data = response.json()
        
        user = await db.users.find_one({"email": oauth_data["email"]})
        
        if not user:
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            user = {
                "user_id": user_id,
                "email": oauth_data["email"],
                "full_name": oauth_data["name"],
                "picture": oauth_data.get("picture", ""),
                "auth_provider": "google",
                "email_verified": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }
            await db.users.insert_one(user)
        else:
            user_id = user.get("user_id") or str(user.get("_id"))
        
        session_token = oauth_data["session_token"]
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        await db.user_sessions.update_one(
            {"email": oauth_data["email"]},
            {
                "$set": {
                    "user_id": user_id,
                    "session_token": session_token,
                    "expires_at": expires_at,
                    "updated_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        return {
            "access_token": session_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": oauth_data["email"],
                "full_name": oauth_data["name"],
                "picture": oauth_data.get("picture", "")
            }
        }
    
    except Exception as e:
        logging.error(f"OAuth error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register")
async def register(user_data: UserRegister):
    """Register a new user"""
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    verification_token = secrets.token_urlsafe(32)
    
    new_user = {
        "user_id": user_id,
        "email": user_data.email,
        "hashed_password": get_password_hash(user_data.password),
        "full_name": user_data.full_name,
        "email_verified": False,
        "verification_token": verification_token,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(new_user)
    
    asyncio.create_task(send_verification_email(
        user_data.email, 
        verification_token,
        user_data.full_name
    ))
    
    return {
        "message": "Registration successful! Please check your email to verify your account.",
        "email": user_data.email
    }


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login with email and password"""
    user = await db.users.find_one({"email": credentials.email})
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.get("hashed_password"):
        raise HTTPException(
            status_code=400, 
            detail="This account uses Google Sign-In. Please login with Google."
        )
    
    if not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.get("email_verified", False):
        raise HTTPException(
            status_code=403, 
            detail="Please verify your email before logging in. Check your inbox for the verification link."
        )
    
    access_token = create_access_token(data={"sub": user["email"]})
    user_id = str(user.get("_id")) if user.get("_id") else user.get("user_id", "")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": user["email"],
            "full_name": user.get("full_name", ""),
            "created_at": user.get("created_at", "")
        }
    }


@router.get("/verify-email")
async def verify_email(token: str):
    """Verify user email with token"""
    user = await db.users.find_one({"verification_token": token})
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    
    if user.get("email_verified"):
        return {"message": "Email already verified"}
    
    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"email_verified": True},
            "$unset": {"verification_token": ""}
        }
    )
    
    return {"message": "Email verified successfully! You can now log in."}


@router.post("/resend-verification")
async def resend_verification(email: EmailStr):
    """Resend verification email"""
    user = await db.users.find_one({"email": email})
    
    if not user:
        return {"message": "If the email exists, a verification link has been sent"}
    
    if user.get("email_verified"):
        raise HTTPException(status_code=400, detail="Email already verified")
    
    new_token = secrets.token_urlsafe(32)
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"verification_token": new_token}}
    )
    
    asyncio.create_task(send_verification_email(user["email"], new_token, user["full_name"]))
    
    return {"message": "Verification email sent! Please check your inbox."}
