import enum

from pydantic import BaseModel, Field, ConfigDict, validator
from typing import Optional, List
from datetime import datetime
import re

from app.modules.admin.models import UserRole, UserStatus


# Base schemas with ORM mode
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# User schemas
class UserBase(BaseSchema):
    phone_number: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


class UserCreate(UserBase):
    """Create user (all fields optional except phone)"""
    # employee_code: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')
    role: Optional[UserRole] = Field(default=UserRole.EMPLOYEE)
    status: Optional[UserStatus] = Field(default=UserStatus.ACTIVE)

    pass


class UserUpdate(BaseSchema):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    role: Optional[UserRole] = Field(default=None)
    status: Optional[UserStatus] = Field(default=None)
    email: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    # employee_code: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')


class UserOut(BaseSchema):
    id: int
    phone_number: str
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: Optional[str]
    email: Optional[str]
    employee_code: Optional[str]
    role: str
    status: str
    is_phone_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]


class UserDetailOut(UserOut):
    last_login_ip: Optional[str]
    phone_verified_at: Optional[datetime]


# OTP schemas
class OTPRequest(BaseModel):
    phone_number: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    purpose: str = "login"  # login or register


class OTPVerify(BaseModel):
    phone_number: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    otp: str = Field(..., min_length=4, max_length=6)


class OTPResponse(BaseModel):
    ok: bool
    message: str
    expires_in: int  # seconds


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
    is_new_user: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: str  # phone_number
    user_id: int
    exp: int
