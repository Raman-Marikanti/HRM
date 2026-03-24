"""
Standard utilities for HRMS response formatting and audit logging
Follows Indian HRMS standard operating procedures
"""

from typing import Any, Optional, Dict, List
from datetime import datetime
import logging
import uuid
from contextlib import contextmanager

from sqlalchemy.orm import Session
from fastapi import Request, status

from app.core.schemas import StandardResponse, AuditLog
from app.core.errors import HRMSException, ErrorCodes


logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Utility class for formatting standardized responses"""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Operation successful",
        status_code: int = status.HTTP_200_OK,
        request_id: Optional[str] = None
    ) -> StandardResponse:
        """Format a success response"""
        return StandardResponse(
            status="success",
            code=status_code,
            message=message,
            data=data,
            request_id=request_id
        )
    
    @staticmethod
    def created(
        data: Any = None,
        message: str = "Resource created successfully",
        request_id: Optional[str] = None
    ) -> StandardResponse:
        """Format a created (201) response"""
        return ResponseFormatter.success(
            data=data,
            message=message,
            status_code=status.HTTP_201_CREATED,
            request_id=request_id
        )
    
    @staticmethod
    def error(
        message: str,
        error_code: str = ErrorCodes.INTERNAL_SERVER_ERROR,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        request_id: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> StandardResponse:
        """Format an error response"""
        return StandardResponse(
            status="error",
            code=status_code,
            message=message,
            data={"error_code": error_code, **(details or {})},
            request_id=request_id
        )
    
    @staticmethod
    def paginated(
        items: List[Any],
        total: int,
        skip: int,
        limit: int,
        message: str = "Data retrieved successfully",
        request_id: Optional[str] = None
    ) -> Dict:
        """Format a paginated response"""
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        current_page = (skip // limit) + 1 if limit > 0 else 1
        
        return {
            "status": "success",
            "code": 200,
            "message": message,
            "data": items,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "current_page": current_page,
                "total_pages": total_pages
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id
        }


class AuditLogger:
    """Utility class for audit logging"""
    
    AUDIT_LOGGER = logging.getLogger("audit")
    
    @staticmethod
    def log_action(
        db: Session,
        user_id: int,
        user_phone: str,
        module: str,
        action: str,
        resource_type: str,
        resource_id: Optional[int],
        ip_address: str,
        user_agent: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        status_str: str = "success",
        remarks: Optional[str] = None
    ):
        """Log an audit action to database and file"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                user_phone=user_phone,
                module=module,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                old_values=old_values,
                new_values=new_values,
                status=status_str,
                ip_address=ip_address,
                user_agent=user_agent,
                remarks=remarks
            )
            
            # Log to file
            AuditLogger.AUDIT_LOGGER.info(
                f"AUDIT | {module} | {action} | {resource_type}:{resource_id} | "
                f"User:{user_id}({user_phone}) | {ip_address} | Status:{status_str}"
            )
            
            return audit_log
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")
    
    @staticmethod
    def log_failed_action(
        user_id: Optional[int],
        user_phone: Optional[str],
        module: str,
        action: str,
        ip_address: str,
        user_agent: str,
        error_message: str
    ):
        """Log a failed action"""
        AuditLogger.AUDIT_LOGGER.warning(
            f"AUDIT | {module} | {action} | User:{user_id}({user_phone}) | "
            f"{ip_address} | Status:failed | Error:{error_message}"
        )


class RequestContextManager:
    """Manage request context for audit logging"""
    
    @staticmethod
    def get_request_id() -> str:
        """Generate unique request ID"""
        return str(uuid.uuid4())[:8]
    
    @staticmethod
    def get_client_info(request: Request) -> tuple:
        """Extract client IP and user agent from request"""
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Check for X-Forwarded-For header (for proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return client_ip, user_agent


@contextmanager
def handle_exceptions():
    """Context manager for standardized exception handling"""
    try:
        yield
    except HRMSException as e:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="An internal server error occurred",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def convert_hrms_exception_to_response(exc: HRMSException, request_id: str) -> Dict:
    """Convert HRMSException to standard response"""
    return {
        "status": "error",
        "code": exc.http_status,
        "message": exc.message,
        "data": {
            "error_code": exc.error_code,
            "field": exc.field,
            **exc.details
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": request_id
    }
