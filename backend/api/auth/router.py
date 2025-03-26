from fastapi import APIRouter, HTTPException, status, Depends, Response, Cookie
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
import logging

from db.supabase_client import authOperations

# Configure logger
logger = logging.getLogger(__name__)

# Router for authentication
router = APIRouter()

# Models
class SignUpRequest(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password", min_length=6)
    full_name: Optional[str] = Field(None, description="User's full name")

class SignInRequest(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")

class AuthResponse(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    success: bool
    message: str
    session: Optional[str] = None

# Routes
@router.post("/signup", response_model=AuthResponse)
async def sign_up(request: SignUpRequest):
    """Sign up a new user."""
    try:
        # Create user metadata
        metadata = {}
        if request.full_name:
            metadata["full_name"] = request.full_name
        
        # Sign up user
        result = await authOperations.sign_up(
            email=request.email,
            password=request.password,
            metadata=metadata
        )
        
        # Return success response
        return {
            "user_id": result.get("user_id"),
            "email": result.get("email"),
            "success": True,
            "message": "User signed up successfully. Please check your email for verification.",
            "session": result.get("session")
        }
    except Exception as e:
        logger.error(f"Sign-up error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sign-up failed: {str(e)}"
        )

@router.post("/signin", response_model=AuthResponse)
async def sign_in(request: SignInRequest, response: Response):
    """Sign in an existing user."""
    try:
        # Sign in user
        result = await authOperations.sign_in(
            email=request.email,
            password=request.password
        )
        
        # Set session cookie (for browser clients)
        if result.get("session"):
            response.set_cookie(
                key="sb-auth-token",
                value=result["session"],
                httponly=True,
                max_age=3600,  # 1 hour
                samesite="strict",
                secure=True
            )
        
        # Return success response
        return {
            "user_id": result.get("user_id"),
            "email": result.get("email"),
            "success": True,
            "message": "User signed in successfully",
            "session": result.get("session")
        }
    except Exception as e:
        logger.error(f"Sign-in error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Sign-in failed: {str(e)}"
        )

@router.get("/user", response_model=Dict[str, Any])
async def get_current_user():
    """Get the currently authenticated user."""
    try:
        # Get current user
        user = await authOperations.get_current_user()
        
        if user:
            return user
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )

@router.post("/signout", response_model=Dict[str, Any])
async def sign_out(response: Response):
    """Sign out the current user."""
    try:
        # Sign out user
        success = await authOperations.sign_out()
        
        # Clear session cookie
        response.delete_cookie(key="sb-auth-token")
        
        return {
            "success": success,
            "message": "User signed out successfully"
        }
    except Exception as e:
        logger.error(f"Sign-out error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sign-out failed: {str(e)}"
        ) 