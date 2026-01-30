"""
Phone Number + OTP Authentication routes using Twilio SMS
"""
import os
import uuid
import random
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

import sys
sys.path.insert(0, '/app/backend')

from database import db
from routes.auth import create_access_token

router = APIRouter(prefix="/auth/phone", tags=["Phone Authentication"])

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

# Initialize Twilio client
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        logging.info("Twilio client initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize Twilio client: {e}")


# ==================== PYDANTIC MODELS ====================

class SendOTPRequest(BaseModel):
    phone_number: str  # E.164 format: +1234567890

class VerifyOTPRequest(BaseModel):
    phone_number: str
    otp_code: str
    full_name: str = None  # Optional, for new user registration


# ==================== HELPER FUNCTIONS ====================

def generate_otp() -> str:
    """Generate a 6-digit OTP code"""
    return str(random.randint(100000, 999999))


def format_phone_number(phone: str) -> str:
    """Ensure phone number is in E.164 format"""
    phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not phone.startswith("+"):
        # Assume US number if no country code
        if len(phone) == 10:
            phone = "+1" + phone
        elif len(phone) == 11 and phone.startswith("1"):
            phone = "+" + phone
    return phone


# ==================== API ENDPOINTS ====================

@router.post("/send-otp")
async def send_otp(request: SendOTPRequest):
    """Send OTP to phone number via Twilio SMS"""
    try:
        if not twilio_client:
            raise HTTPException(
                status_code=500, 
                detail="SMS service not configured. Please contact support."
            )
        
        phone_number = format_phone_number(request.phone_number)
        
        # Validate phone number format
        if not phone_number.startswith("+") or len(phone_number) < 10:
            raise HTTPException(
                status_code=400, 
                detail="Invalid phone number format. Please use format: +1234567890"
            )
        
        # Generate OTP
        otp_code = generate_otp()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        # Store OTP in database
        await db.phone_otps.update_one(
            {"phone_number": phone_number},
            {
                "$set": {
                    "otp_code": otp_code,
                    "expires_at": expires_at,
                    "attempts": 0,
                    "created_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        # Send SMS via Twilio
        try:
            message = twilio_client.messages.create(
                body=f"Your ContentFlow verification code is: {otp_code}. This code expires in 10 minutes.",
                from_=TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            logging.info(f"OTP sent to {phone_number[-4:]}, Message SID: {message.sid}")
        except TwilioRestException as e:
            logging.error(f"Twilio error: {e}")
            # Clean up stored OTP on failure
            await db.phone_otps.delete_one({"phone_number": phone_number})
            
            if "unverified" in str(e).lower():
                raise HTTPException(
                    status_code=400,
                    detail="This phone number is not verified for testing. Please use a verified number or contact support."
                )
            raise HTTPException(
                status_code=400,
                detail="Failed to send SMS. Please check your phone number and try again."
            )
        
        return {
            "success": True,
            "message": "OTP sent successfully",
            "phone_number": f"***{phone_number[-4:]}",  # Masked for security
            "expires_in": 600  # 10 minutes in seconds
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error sending OTP: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send OTP. Please try again.")


@router.post("/verify-otp")
async def verify_otp(request: VerifyOTPRequest):
    """Verify OTP and authenticate/register user"""
    try:
        phone_number = format_phone_number(request.phone_number)
        
        # Get stored OTP
        otp_record = await db.phone_otps.find_one({"phone_number": phone_number})
        
        if not otp_record:
            raise HTTPException(
                status_code=400,
                detail="No OTP found for this phone number. Please request a new code."
            )
        
        # Check if OTP is expired
        if otp_record.get("expires_at") and otp_record["expires_at"] < datetime.now(timezone.utc):
            await db.phone_otps.delete_one({"phone_number": phone_number})
            raise HTTPException(
                status_code=400,
                detail="OTP has expired. Please request a new code."
            )
        
        # Check attempts (max 5)
        attempts = otp_record.get("attempts", 0)
        if attempts >= 5:
            await db.phone_otps.delete_one({"phone_number": phone_number})
            raise HTTPException(
                status_code=400,
                detail="Too many failed attempts. Please request a new code."
            )
        
        # Verify OTP
        if otp_record.get("otp_code") != request.otp_code:
            # Increment attempts
            await db.phone_otps.update_one(
                {"phone_number": phone_number},
                {"$inc": {"attempts": 1}}
            )
            remaining = 5 - attempts - 1
            raise HTTPException(
                status_code=400,
                detail=f"Invalid OTP code. {remaining} attempts remaining."
            )
        
        # OTP verified - delete it
        await db.phone_otps.delete_one({"phone_number": phone_number})
        
        # Check if user exists
        user = await db.users.find_one({"phone_number": phone_number})
        
        if not user:
            # Create new user
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            full_name = request.full_name or f"User {phone_number[-4:]}"
            
            user = {
                "user_id": user_id,
                "phone_number": phone_number,
                "full_name": full_name,
                "auth_provider": "phone",
                "phone_verified": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }
            await db.users.insert_one(user)
            is_new_user = True
        else:
            user_id = user.get("user_id") or str(user.get("_id"))
            is_new_user = False
            
            # Update phone_verified status
            await db.users.update_one(
                {"phone_number": phone_number},
                {"$set": {"phone_verified": True}}
            )
        
        # Create JWT token
        access_token = create_access_token(data={"sub": phone_number})
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "is_new_user": is_new_user,
            "user": {
                "id": user_id,
                "phone_number": f"***{phone_number[-4:]}",
                "full_name": user.get("full_name", ""),
                "created_at": user.get("created_at", "")
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error verifying OTP: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to verify OTP. Please try again.")


@router.post("/resend-otp")
async def resend_otp(request: SendOTPRequest):
    """Resend OTP to phone number (with rate limiting)"""
    try:
        phone_number = format_phone_number(request.phone_number)
        
        # Check if there's a recent OTP request (rate limiting - 1 minute)
        recent_otp = await db.phone_otps.find_one({
            "phone_number": phone_number,
            "created_at": {"$gt": datetime.now(timezone.utc) - timedelta(minutes=1)}
        })
        
        if recent_otp:
            raise HTTPException(
                status_code=429,
                detail="Please wait 1 minute before requesting a new code."
            )
        
        # Delete old OTP and send new one
        await db.phone_otps.delete_one({"phone_number": phone_number})
        
        # Reuse send_otp logic
        return await send_otp(request)
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error resending OTP: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to resend OTP. Please try again.")
