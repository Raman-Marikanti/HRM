from datetime import timedelta
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, logger, status, Request
from requests import session
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import require_roles, get_current_user
from app.modules.admin import services
from app.modules.admin.models import User
from app.modules.admin.schemas import (
    UserCreate, UserOut, UserDetailOut, UserUpdate,
    OTPRequest, OTPVerify, OTPResponse, LoginResponse
)
from app.modules.admin.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/admin/auth", tags=["Authentication"])

logger = logging.getLogger(__name__)
# Helper function for error handling
def handle_service_error(db: Session, func, *args, **kwargs):
    """Helper function to handle service errors"""
    try:
        result = func(*args, **kwargs)
        db.commit()
        return result
    except services.UserNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.UserAlreadyExistsError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except services.InvalidOTPError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except services.AccountLockedError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except services.AuthServiceError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# ============================================================================
# OTP Authentication Endpoints
# ============================================================================

@router.post("/send-otp", response_model=OTPResponse)
def send_otp(
    otp_request: OTPRequest,
    db: Session = Depends(get_db)
):
    """Send OTP to phone number for login/registration"""
    # verify user exists or create a new one (without committing yet)
    User = services.get_user_by_phone(db, otp_request.phone_number)
    if not User:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found. Please register first.")
    if User.employee_code == 'admin':
        return OTPResponse(
            ok=True,
            message="OTP sent successfully (admin user)",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    result = services.send_otp(
        otp_request.phone_number, 
        otp_request.purpose
    )
    return OTPResponse(  
        ok=True,
        message=result["message"],
        expires_in=result["expires_in"]
    )


@router.post("/verify-otp", response_model=LoginResponse)
def verify_otp_and_login(
    otp_verify: OTPVerify,
    request: Request,
    db: Session = Depends(get_db)
):
    """Verify OTP and login/register user"""
    try:
        # Authenticate with OTP
        auth_result = services.authenticate_with_otp(
            db, 
            otp_verify.phone_number, 
            otp_verify.otp,
            request.client.host
        )
        
        user = auth_result["user"]
        is_new_user = auth_result["is_new_user"]
        
        # Create access token
        access_token = create_access_token(
            subject=user.phone_number,
            extra_data={
                "user_id": user.id,
                "roles":  [user.role]
            }
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user,
            is_new_user=is_new_user
        )
        
    except services.InvalidOTPError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except services.AccountLockedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/logout")
def logout():
    """Logout user (client should discard token)"""
    return {"message": "Successfully logged out"}


# ============================================================================
# User Profile Endpoints
# ============================================================================

# @router.get("/me", response_model=UserOut)
# def get_current_user_info(
#     current_user: dict = Depends(require_roles())  # Just requires authentication
# ):
#     """Get current user information"""
#     return current_user["user"]


# @router.put("/me", response_model=UserOut)
# def update_current_user(
#     updates: UserUpdate,
#     db: Session = Depends(get_db),
#     current_user: dict = Depends(require_roles())
# ):
#     """Update current user profile"""
#     return handle_service_error(
#         db, services.update_user,
#         db, current_user["user_id"], updates
#     )


# @router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
# def delete_current_user(
#     db: Session = Depends(get_db),
#     current_user: dict = Depends(require_roles())
# ):
#     """Delete current user account"""
#     handle_service_error(
#         db, services.delete_user,
#         db, current_user["user_id"], soft_delete=True
#     )
#     return None


# ============================================================================
# Admin Endpoints
# ============================================================================

@router.get("/users", response_model=List[UserOut])
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    # current_user: dict = Depends(require_roles("admin"))
):
    """Get all users (Admin only)"""
    from sqlalchemy import select
    users = db.execute(
        select(User).where(User.deleted_at.is_(None))
        .offset(skip).limit(limit)
    ).scalars().all()
    return users


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    user_create: UserCreate,
    db: Session = Depends(get_db),
    # current_user: dict = Depends(require_roles("admin"))
):
    """Create a new user (Admin only)"""
    return handle_service_error(db, services.create_user, db, user_create)

@router.get("/users/{user_id}", response_model=UserDetailOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    # current_user: dict = Depends(require_roles("admin", "hr"))
):
    """Get user by ID (Admin/HR only)"""
    user = services.get_user_by_id(db, user_id)
    if not user or user.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    updates: UserUpdate,
    db: Session = Depends(get_db),
    # current_user: dict = Depends(require_roles("admin"))
):
    """Update user (Admin only)"""
    return handle_service_error(db, services.update_user, db, user_id, updates)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    # current_user: dict = Depends(require_roles("admin"))
):
    """Delete user (Admin only)"""
    handle_service_error(db, services.delete_user, db, user_id, soft_delete=True)
    return None


# ============================================================================
# Role-based test endpoints
# ============================================================================

# @router.get("/admin-only")
# def admin_only(
#     current_user: dict = Depends(require_roles("admin"))
# ):
#     """Test endpoint for admin access"""
#     return {
#         "message": "Welcome admin",
#         "user": current_user["employee_code"] or current_user["phone_number"],
#         "roles": current_user["roles"]
#     }


# @router.get("/hr-only")
# def hr_only(
#     current_user: dict = Depends(require_roles("hr"))
# ):
#     """Test endpoint for HR access"""
#     return {
#         "message": "Welcome HR",
#         "user": current_user["employee_code"] or current_user["phone_number"]
#     }


# @router.get("/employee-only")
# def employee_only(
#     current_user: dict = Depends(require_roles("employee"))
# ):
#     """Test endpoint for employee access"""
#     return {
#         "message": "Welcome employee",
#         "user": current_user["employee_code"] or current_user["phone_number"]
#     }