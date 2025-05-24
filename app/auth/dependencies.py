from datetime import datetime, timedelta
from typing import Annotated, Dict, Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config import settings
from app.db.prisma_client import get_prisma

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="ai/auth/token", auto_error=False)

class TokenData(BaseModel):
    username: Optional[str] = None
    sub: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    image: Optional[str] = None

def verify_password(plain_password, hashed_password):
    """Verify password against hashed version"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hash password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, user: Optional[dict] = None):
    """Create JWT token with additional user fields (name, image, iat)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})  # Adding "iat" (issued at)
    
    # Add user's additional fields to the token
    if user:
        to_encode["name"] = user.get("name", None)
        to_encode["image"] = user.get("image", None)
    
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Get current user from JWT token - compatible with NestJS tokens
    Handle tokens from both FastAPI and NestJS authentication systems
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the JWT token
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=["HS256"]
        )
        
        # NestJS uses 'email' and 'sub' (for user ID)
        # FastAPI uses 'sub' for email/username
        # Handle both formats
        
        email = payload.get("email") or payload.get("sub")
        user_id = payload.get("sub")
        
        if not email:
            raise credentials_exception
            
        token_data = TokenData(
            username=email,
            sub=user_id,
            email=email,
            name=payload.get("name"),
            image=payload.get("image")
        )
        
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise credentials_exception
    
    async with get_prisma() as prisma:
        # First try to find user by email
        user = await prisma.user.find_unique(
            where={
                'email': token_data.email
            }
        )
        
        if not user:
            # If user not found by email, it might be using NestJS ID as sub
            # Try to find by ID if it's available
            if token_data.sub and token_data.sub != token_data.email:
                try:
                    user = await prisma.user.find_unique(
                        where={
                            'id': token_data.sub
                        }
                    )
                except Exception:
                    # If ID lookup fails, it might not be a valid ID format
                    pass
        
        if not user:
            raise credentials_exception
        
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "image": getattr(user, "image", None)
        }

# Optional function to specifically handle NestJS tokens
async def validate_nestjs_token(token: str):
    """
    Validate a token originating from NestJS
    Used for debugging and token verification
    """
    try:
        # Decode the JWT token
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=["HS256"]
        )
        
        # NestJS format expected
        email = payload.get("email")
        user_id = payload.get("sub")
        
        if not email or not user_id:
            return {"valid": False, "error": "Missing email or user ID in token"}
        
        async with get_prisma() as prisma:
            user = await prisma.user.find_unique(
                where={
                    'email': email
                }
            )
            
            if not user:
                return {"valid": False, "error": "User not found"}
            
            return {
                "valid": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name
                }
            }
            
    except JWTError as e:
        return {"valid": False, "error": str(e)}