"""
Standard error definitions and utilities for HRMS
Follows Indian HRMS standard operating procedures
"""

from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status


# Standard Error Codes
class ErrorCodes:
    """Standard error codes used across HRMS"""
    # Validation errors (4000-4999)
    INVALID_INPUT = "ERR_4000"
    REQUIRED_FIELD_MISSING = "ERR_4001"
    DATE_RANGE_INVALID = "ERR_4002"
    DUPLICATE_ENTRY = "ERR_4003"
    INVALID_DATE_FORMAT = "ERR_4004"
    INVALID_TIME_FORMAT = "ERR_4005"
    INVALID_STATUS = "ERR_4006"
    INVALID_EMPLOYEE_CODE = "ERR_4007"
    
    # Authorization errors (4030-4039)
    UNAUTHORIZED = "ERR_4030"
    FORBIDDEN = "ERR_4031"
    INSUFFICIENT_PERMISSIONS = "ERR_4032"
    
    # Resource errors (4040-4099)
    RESOURCE_NOT_FOUND = "ERR_4040"
    EMPLOYEE_NOT_FOUND = "ERR_4041"
    DEPARTMENT_NOT_FOUND = "ERR_4042"
    DESIGNATION_NOT_FOUND = "ERR_4043"
    SHIFT_NOT_FOUND = "ERR_4044"
    LEAVE_REQUEST_NOT_FOUND = "ERR_4045"
    ATTENDANCE_RECORD_NOT_FOUND = "ERR_4046"
    USER_NOT_FOUND = "ERR_4047"
    
    # Business logic errors (5000-5999)
    DUPLICATE_ATTENDANCE = "ERR_5000"
    DUPLICATE_EMPLOYEE = "ERR_5001"
    CANNOT_DELETE_ACTIVE_EMPLOYEE = "ERR_5002"
    INVALID_SHIFT_TIME = "ERR_5003"
    INSUFFICIENT_LEAVE_BALANCE = "ERR_5004"
    LEAVE_PERIOD_OVERLAPS = "ERR_5005"
    ATTENDANCE_ALREADY_MARKED = "ERR_5006"
    INVALID_CHECK_IN_TIME = "ERR_5007"
    CHECK_OUT_BEFORE_CHECK_IN = "ERR_5008"
    
    # System errors (5000+)
    INTERNAL_SERVER_ERROR = "ERR_5999"


class HRMSException(Exception):
    """Base exception for HRMS"""
    def __init__(
        self,
        error_code: str,
        message: str,
        http_status: int = status.HTTP_400_BAD_REQUEST,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.http_status = http_status
        self.field = field
        self.details = details or {}
        super().__init__(message)


class ValidationError(HRMSException):
    """Validation error"""
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            error_code=ErrorCodes.INVALID_INPUT,
            message=message,
            http_status=status.HTTP_400_BAD_REQUEST,
            field=field,
            details=details
        )


class ResourceNotFoundError(HRMSException):
    """Resource not found error"""
    def __init__(self, resource_type: str, resource_id: Optional[int] = None):
        message = f"{resource_type} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        
        error_code_map = {
            "Employee": ErrorCodes.EMPLOYEE_NOT_FOUND,
            "Department": ErrorCodes.DEPARTMENT_NOT_FOUND,
            "Designation": ErrorCodes.DESIGNATION_NOT_FOUND,
            "Shift": ErrorCodes.SHIFT_NOT_FOUND,
            "LeaveRequest": ErrorCodes.LEAVE_REQUEST_NOT_FOUND,
            "Attendance": ErrorCodes.ATTENDANCE_RECORD_NOT_FOUND,
            "User": ErrorCodes.USER_NOT_FOUND,
        }
        
        error_code = error_code_map.get(resource_type, ErrorCodes.RESOURCE_NOT_FOUND)
        
        super().__init__(
            error_code=error_code,
            message=message,
            http_status=status.HTTP_404_NOT_FOUND
        )


class DuplicateError(HRMSException):
    """Duplicate resource error"""
    def __init__(self, resource_type: str, field: Optional[str] = None):
        message = f"{resource_type} already exists"
        if field:
            message += f" with this {field}"
        
        error_code_map = {
            "Employee": ErrorCodes.DUPLICATE_EMPLOYEE,
            "Attendance": ErrorCodes.DUPLICATE_ATTENDANCE,
        }
        
        error_code = error_code_map.get(resource_type, ErrorCodes.DUPLICATE_ENTRY)
        
        super().__init__(
            error_code=error_code,
            message=message,
            http_status=status.HTTP_409_CONFLICT,
            field=field
        )


class BusinessLogicError(HRMSException):
    """Business logic validation error"""
    def __init__(self, error_code: str, message: str):
        super().__init__(
            error_code=error_code,
            message=message,
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class AuthorizationError(HRMSException):
    """Authorization/permission error"""
    def __init__(self, message: str = "Access denied. Insufficient permissions."):
        super().__init__(
            error_code=ErrorCodes.FORBIDDEN,
            message=message,
            http_status=status.HTTP_403_FORBIDDEN
        )


class AuthenticationError(HRMSException):
    """Authentication error"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            error_code=ErrorCodes.UNAUTHORIZED,
            message=message,
            http_status=status.HTTP_401_UNAUTHORIZED
        )
