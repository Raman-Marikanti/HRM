from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.admin import services
from sqlalchemy import select

# OAuth2 scheme (using phone number as username)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/verify-otp", auto_error=False)

# Token settings
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES or 30 * 24 * 60  # 30 days
ALGORITHM = "HS256"
SECRET_KEY = settings.SECRET_KEY


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> str:
    """Create a JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.utcnow()
    }
    
    if extra_data:
        to_encode.update(extra_data)
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a JWT token and return payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
            return None
        
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get current user from token with employee link"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    # Verify token
    payload = verify_token(token)
    if not payload:
        raise credentials_exception
    
    phone_number: str = payload.get("sub")
    user_id: int = payload.get("user_id")
    
    if not phone_number or not user_id:
        raise credentials_exception
    
    # Get user from database
    user = services.get_user_by_id(db, user_id)
    if not user or user.deleted_at:
        raise credentials_exception
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Get employee_id from employee table if user is an employee
    employee_id = None
    try:
        if hasattr(user, 'employee'):
            employee_id = user.employee.id if user.employee else None
        else:
            # Query employee directly
            from app.modules.employee.models import Employee
            employee = db.execute(
                select(Employee).where(Employee.user_id == user_id)
            ).scalar_one_or_none()
            employee_id = employee.id if employee else None
    except Exception:
        # If employee lookup fails, continue without employee_id
        employee_id = None
    
    # Return user info with roles and employee link
    return {
        "id": user.id,
        "user_id": user.id,
        "employee_id": employee_id,
        "phone_number": user.phone_number,
        "employee_code": user.employee_code,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "roles": user.roles + [user.role],
        "user": user
    }