from select import select

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

from app.modules.admin import router as auth_router
from app.modules.admin.models import User
from app.modules.employee import emp_router
from app.modules.attendance import attendance_router
from app.core.database import engine
from app.core.database import SessionLocal

from app.core.config import DATABASE_URL
from app.core.errors import HRMSException
from app.core.utils import RequestContextManager, convert_hrms_exception_to_response


logger = logging.getLogger(__name__)

app = FastAPI(title="Human Resource Management System API", version="1.0.0")


# Global exception handlers for standardized error responses
@app.exception_handler(HRMSException)
async def hrms_exception_handler(request: Request, exc: HRMSException):
    """Handle HRMS custom exceptions"""
    request_id = RequestContextManager.get_request_id()
    response_data = convert_hrms_exception_to_response(exc, request_id)
    return JSONResponse(status_code=exc.http_status, content=response_data)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI validation errors with standard format"""
    request_id = RequestContextManager.get_request_id()
    
    errors = []
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"][1:]) if len(error["loc"]) > 1 else None
        errors.append({
            "field": field,
            "error_code": "ERR_4000",
            "message": error["msg"]
        })
    
    response_data = {
        "status": "error",
        "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "message": "Validation failed",
        "data": {
            "error_code": "ERR_4000",
            "errors": errors
        },
        "request_id": request_id,
        "timestamp": None
    }
    
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=response_data)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
       "*"
    ],
    allow_credentials=True,   # set True only if using cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    from app.core.utils import ResponseFormatter
    return ResponseFormatter.success(
        data={"api_version": "1.0.0", "environment": "production"},
        message="HRMS API is running"
    )



app.include_router(auth_router)
# app.include_router(emp_router)
# app.include_router(attendance_router)



@app.on_event("startup")
async def on_startup():
    try:
        from scripts.create_admin import create_admin
        session = SessionLocal()
        admin = session.query(select(User)).filter(User.employee_code == 'admin').first()
        if not admin:
            create_admin()
        else:
            logger.info("Admin user already exists, skipping creation.")
        session.close()
    except Exception as e:
        logger.error(f"Error during startup: {e}")
