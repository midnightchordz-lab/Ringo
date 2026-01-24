"""
Authentication routes - handles user registration, login, OAuth (Google, Microsoft)
"""
import uuid
import secrets
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends, Form, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import EmailStr
import httpx
import resend
import bcrypt
from jose import JWTError, jwt

import sys
sys.path.insert(0, '/app/backend')

from database import db
from config import (
    RESEND_API_KEY, SENDER_EMAIL, FRONTEND_URL, 
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
    MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_TENANT
)
from models.schemas import UserRegister, UserLogin, Token, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Initialize Resend
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ==================== PASSWORD HELPERS ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using bcrypt directly"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt directly"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


# ==================== JWT HELPERS ====================

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Validate JWT token and return current user"""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        # Check if it's an Emergent OAuth session token
        session = await db.user_sessions.find_one({
            "session_token": token,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })
        if session:
            user = await db.users.find_one({"email": session.get("email")})
            if not user:
                user = await db.users.find_one({"user_id": session.get("user_id")})
            if user:
                return user
        raise credentials_exception
    
    user = await db.users.find_one({"email": email})
    if user is None:
        raise credentials_exception
    
    return user


# ==================== EMAIL HELPERS ====================

async def send_verification_email(email: str, token: str, name: str):
    """Send verification email using Resend"""
    if not RESEND_API_KEY:
        logging.warning(f"[DEV MODE] No Resend API key. Verification link: {FRONTEND_URL}/verify-email?token={token}")
        return
    
    verification_link = f"{FRONTEND_URL}/verify-email?token={token}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #0a0a0a; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
            <div style="background: linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%); padding: 40px; text-align: center; border-radius: 16px 16px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">Welcome to ContentFlow!</h1>
            </div>
            <div style="padding: 40px; background: #18181b; color: #ffffff; border-radius: 0 0 16px 16px;">
                <h2 style="color: #BEF264; margin-top: 0;">Hi {name}!</h2>
                <p style="color: #a1a1aa; line-height: 1.6; font-size: 16px;">
                    Thanks for signing up! Please verify your email address to get started with discovering viral content.
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_link}" 
                       style="background: #BEF264; color: #000; padding: 15px 40px; 
                              text-decoration: none; border-radius: 30px; font-weight: bold;
                              display: inline-block; font-size: 16px;">
                        Verify Email Address
                    </a>
                </div>
                <p style="color: #71717a; font-size: 14px; margin-top: 30px;">
                    If you didn't create an account, you can safely ignore this email.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        resend.Emails.send({
            "from": SENDER_EMAIL,
            "to": email,
            "subject": "Verify your ContentFlow account",
            "html": html_content
        })
        logging.info(f"Verification email sent to {email}")
    except Exception as e:
        logging.error(f"Failed to send verification email: {e}")


# ==================== GOOGLE OAUTH ====================

@router.post("/google-oauth")
async def google_oauth_callback(session_id: str = Form(...)):
    """Process Google OAuth via Emergent Auth"""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id},
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Invalid session ID")
            
            oauth_data = response.json()
        
        # Check if user exists
        user = await db.users.find_one({"email": oauth_data["email"]})
        
        if not user:
            # Create new user
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
        
        # Store Emergent session token
        session_token = oauth_data["session_token"]
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        await db.user_sessions.update_one(
            {"email": oauth_data["email"]},
            {
                "$set": {
                    "user_id": user_id,
                    "email": oauth_data["email"],
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
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Google OAuth error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MICROSOFT OAUTH ====================

@router.get("/microsoft/login")
async def microsoft_login(request: Request):
    """Redirect to Microsoft OAuth login"""
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    
    # Determine the correct frontend URL
    if origin and "localhost" not in origin:
        frontend_url = origin
    elif referer:
        from urllib.parse import urlparse
        parsed = urlparse(referer)
        frontend_url = f"{parsed.scheme}://{parsed.netloc}"
    else:
        frontend_url = FRONTEND_URL
    
    redirect_uri = f"{frontend_url}/auth/microsoft/callback"
    
    # Build Microsoft OAuth URL
    auth_url = (
        f"https://login.microsoftonline.com/{MICROSOFT_TENANT}/oauth2/v2.0/authorize"
        f"?client_id={MICROSOFT_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&response_mode=query"
        f"&scope=openid%20profile%20email%20User.Read"
        f"&state=contentflow_microsoft_auth"
    )
    
    return {"auth_url": auth_url, "redirect_uri": redirect_uri}


@router.post("/microsoft/callback")
async def microsoft_callback(code: str = Form(...), redirect_uri: str = Form(...)):
    """Process Microsoft OAuth callback"""
    try:
        token_url = f"https://login.microsoftonline.com/{MICROSOFT_TENANT}/oauth2/v2.0/token"
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            token_response = await client.post(
                token_url,
                data={
                    "client_id": MICROSOFT_CLIENT_ID,
                    "client_secret": MICROSOFT_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                    "scope": "openid profile email User.Read"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15.0
            )
            
            if token_response.status_code != 200:
                error_detail = token_response.json()
                logging.error(f"Microsoft token error: {error_detail}")
                raise HTTPException(status_code=400, detail="Failed to get access token from Microsoft")
            
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            
            # Get user info from Microsoft Graph
            user_response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0
            )
            
            if user_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get user info from Microsoft")
            
            user_info = user_response.json()
        
        # Extract user data
        email = user_info.get("mail") or user_info.get("userPrincipalName")
        full_name = user_info.get("displayName", "")
        microsoft_id = user_info.get("id")
        
        if not email:
            raise HTTPException(status_code=400, detail="Could not get email from Microsoft account")
        
        # Check if user exists
        user = await db.users.find_one({"email": email})
        
        if not user:
            user_id = str(uuid.uuid4())
            user = {
                "_id": user_id,
                "email": email,
                "full_name": full_name,
                "microsoft_id": microsoft_id,
                "auth_provider": "microsoft",
                "email_verified": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }
            await db.users.insert_one(user)
        else:
            user_id = str(user.get("_id")) or user.get("user_id")
            if not user.get("microsoft_id"):
                await db.users.update_one(
                    {"email": email},
                    {"$set": {"microsoft_id": microsoft_id}}
                )
        
        # Create JWT token
        jwt_token = create_access_token(data={"sub": email})
        
        return {
            "access_token": jwt_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "auth_provider": "microsoft"
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Microsoft OAuth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


# ==================== EMAIL/PASSWORD AUTH ====================

@router.post("/register", response_model=Token)
async def register(user_data: UserRegister):
    """Register a new user with email/password"""
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)
    verification_token = secrets.token_urlsafe(32)
    
    # Auto-verify users since email verification isn't configured
    new_user = {
        "_id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": hashed_password,
        "email_verified": True,  # Auto-verified since Resend API may not be configured
        "verification_token": verification_token,
        "auth_provider": "email",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True
    }
    
    await db.users.insert_one(new_user)
    
    # Try to send verification email (non-blocking)
    if RESEND_API_KEY:
        asyncio.create_task(send_verification_email(user_data.email, verification_token, user_data.full_name))
    
    # Create access token and log user in immediately
    access_token = create_access_token(data={"sub": user_data.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "created_at": new_user["created_at"],
            "email_verified": True
        }
    }


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    """Login with email and password"""
    user = await db.users.find_one({"email": user_data.email})
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # Check if OAuth provider
    if user.get("auth_provider") == "google":
        raise HTTPException(status_code=400, detail="Please sign in with Google")
    if user.get("auth_provider") == "microsoft":
        raise HTTPException(status_code=400, detail="Please sign in with Microsoft")
    
    # Verify password
    if not user.get("hashed_password"):
        raise HTTPException(status_code=400, detail="Invalid account configuration. Please contact support.")
    
    if not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # Check email verification
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


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    user_id = str(current_user.get("_id")) if current_user.get("_id") else current_user.get("user_id", "")
    return {
        "id": user_id,
        "email": current_user.get("email", ""),
        "full_name": current_user.get("full_name", ""),
        "created_at": current_user.get("created_at", "")
    }


@router.get("/verify-email")
async def verify_email(token: str):
    """Verify user's email address"""
    try:
        user = await db.users.find_one({"verification_token": token})
        
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        
        if user.get("email_verified"):
            return {"message": "Email already verified", "success": True}
        
        await db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "email_verified": True,
                    "verified_at": datetime.now(timezone.utc).isoformat()
                },
                "$unset": {"verification_token": ""}
            }
        )
        
        access_token = create_access_token(data={"sub": user["email"]})
        user_id = str(user.get("_id")) if user.get("_id") else user.get("user_id", "")
        
        return {
            "success": True,
            "message": "Email verified successfully!",
            "access_token": access_token,
            "user": {
                "id": user_id,
                "email": user["email"],
                "full_name": user.get("full_name", ""),
                "created_at": user.get("created_at", "")
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Email verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Verification failed")


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
    
    asyncio.create_task(send_verification_email(user["email"], new_token, user.get("full_name", "")))
    
    return {"message": "Verification email sent! Please check your inbox."}
