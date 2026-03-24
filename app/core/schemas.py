"""
Standard response schemas for HRMS API
Follows Indian HRMS standard operating procedures
"""

from datetime import datetime
from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field


class StandardResponse(BaseModel):
    """Standard response wrapper for all API responses"""
    status: str = Field(..., description="Response status: success, error, warning")
    code: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Any] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    request_id: Optional[str] = Field(None, description="Unique request identifier")


class ErrorDetail(BaseModel):
    """Detailed error information"""
    field: Optional[str] = Field(None, description="Field name if specific to a field")
    error_code: str = Field(..., description="Standard error code")
    message: str = Field(..., description="Error message")


class ValidationErrorResponse(BaseModel):
    """Response for validation errors"""
    status: str = "error"
    code: int = 400
    message: str = "Validation failed"
    errors: List[ErrorDetail] = Field(..., description="List of validation errors")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel):
    """Response wrapper for paginated data"""
    status: str = "success"
    code: int = 200
    message: str = "Data retrieved successfully"
    data: List[Any] = Field(..., description="List of items")
    pagination: Dict[str, int] = Field(..., description="Pagination metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(BaseModel):
    """Audit log schema for tracking user actions"""
    user_id: int
    user_phone: str
    module: str
    action: str
    resource_type: str
    resource_id: Optional[int]
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    status: str  # success, failed, warning
    ip_address: str
    user_agent: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    remarks: Optional[str] = None
