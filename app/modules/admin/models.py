import uuid

from sqlalchemy import UUID, Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    HR = "hr"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    
    # Optional personal info
    first_name = Column(String(128), nullable=True)
    last_name = Column(String(128), nullable=True)
    email = Column(String(256), unique=True, nullable=False)  # Optional
    employee_code = Column(String, unique=True, nullable=False)  # Optional
    
    # Status and roles
    role = Column(String(50), default=UserRole.EMPLOYEE.value, nullable=False)
    status = Column(String(50), default=UserStatus.ACTIVE.value, nullable=False)
    
    # Phone verification
    is_phone_verified = Column(Boolean, default=False, nullable=False)
    phone_verified_at = Column(DateTime, nullable=True)

    is_employee_created = Column(Boolean, nullable=False, default=False) # To track if employee record is created for this user
    
    # Security
    failed_otp_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete

    @property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or f"User {self.phone_number}"

    @property
    def is_active(self) -> bool:
        """Check if user account is active"""
        if self.deleted_at:
            return False
        if self.locked_until and self.locked_until > datetime.utcnow():
            return False
        return self.status == UserStatus.ACTIVE.value

    def to_dict(self) -> dict:
        """Convert user to dictionary (excluding sensitive data)"""
        return {
            "id": self.id,
            "phone_number": self.phone_number,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "email": self.email,
            "employee_code": self.employee_code,
            "role": self.role,
            "status": self.status,
            "is_phone_verified": self.is_phone_verified,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login_at": self.last_login_at,
        }