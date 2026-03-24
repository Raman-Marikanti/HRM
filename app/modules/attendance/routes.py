from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import require_roles, get_current_user
from app.core.utils import ResponseFormatter, AuditLogger, RequestContextManager
from app.modules.attendance import services
from app.modules.attendance.schemas import (
    # Attendance
    AttendanceCreate, AttendanceOut, AttendanceDetailOut, AttendanceUpdate,
    AttendanceCheckIn, AttendanceCheckOut, AttendanceSummary,
    DateRange,
    
    # Leave
    LeaveRequestCreate, LeaveRequestOut, LeaveRequestUpdate,
    LeaveRequestApprove, LeaveBalance,
    
    # Holiday
    HolidayCreate, HolidayOut, HolidayUpdate,
    
    # Work Shift
    WorkShiftCreate, WorkShiftOut, WorkShiftUpdate,
    EmployeeShiftAssign, EmployeeShiftOut
)
from app.modules.attendance.models import AttendanceStatus, LeaveStatus

router = APIRouter(prefix="/attendance", tags=["Attendance"])


# Helper function for error handling
def handle_service_error(db: Session, func, *args, **kwargs):
    """Helper function to handle service errors"""
    try:
        result = func(*args, **kwargs)
        db.commit()
        return result
    except services.NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.DuplicateError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except services.ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except services.AttendanceServiceError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}")


# Attendance Endpoints (Employee accessible)
@router.post("/check-in", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED)
def check_in(
    data: AttendanceCheckIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("employee", "admin", "hr"))
):
    """Record employee check-in (Employees, Admin, HR)"""
    # Get employee ID from current user
    if not current_user.get("employee_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not an employee")
    
    return handle_service_error(db, services.check_in, db, current_user["employee_id"], data)


@router.post("/check-out", response_model=AttendanceOut)
def check_out(
    data: AttendanceCheckOut,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("employee", "admin", "hr"))
):
    """Record employee check-out (Employees, Admin, HR)"""
    if not current_user.get("employee_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not an employee")
    
    return handle_service_error(db, services.check_out, db, current_user["employee_id"], data)


@router.get("/my-attendance", response_model=List[AttendanceOut])
def get_my_attendance(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("employee", "admin", "hr"))
):
    """Get current user's attendance within date range"""
    if not current_user.get("employee_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not an employee")
    
    date_range = DateRange(start_date=start_date, end_date=end_date)
    return services.get_employee_attendance(db, current_user["employee_id"], date_range)


@router.get("/my-summary", response_model=AttendanceSummary)
def get_my_attendance_summary(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("employee", "admin", "hr"))
):
    """Get current user's attendance summary"""
    if not current_user.get("employee_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not an employee")
    
    try:
        return services.get_attendance_summary(db, current_user["employee_id"], year, month)
    except services.NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# Admin/HR only attendance endpoints
@router.post("/attendances", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED)
def create_attendance(
    data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr"))
):
    """Create attendance record manually (Admin/HR only)"""
    return handle_service_error(db, services.create_attendance, db, data)


@router.get("/attendances/{attendance_id}", response_model=AttendanceDetailOut)
def get_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr", "manager"))
):
    """Get attendance by ID (Admin/HR/Manager only)"""
    attendance = services.get_attendance_by_id(db, attendance_id)
    if not attendance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance not found")
    return attendance


@router.get("/employees/{employee_id}/attendances", response_model=List[AttendanceOut])
def get_employee_attendance(
    employee_id: int,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr", "manager"))
):
    """Get attendance for a specific employee within date range (Admin/HR/Manager only)"""
    date_range = DateRange(start_date=start_date, end_date=end_date)
    return services.get_employee_attendance(db, employee_id, date_range)


@router.get("/attendances", response_model=List[AttendanceDetailOut])
def get_all_attendances(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    employee_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status: Optional[AttendanceStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr"))
):
    """Get all attendance records with filters (Admin/HR only)"""
    return services.get_all_attendance(
        db, skip, limit, employee_id, start_date, end_date, status
    )


@router.put("/attendances/{attendance_id}", response_model=AttendanceOut)
def update_attendance(
    attendance_id: int,
    updates: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr"))
):
    """Update attendance record (Admin/HR only)"""
    return handle_service_error(db, services.update_attendance, db, attendance_id, updates)


@router.delete("/attendances/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin"))
):
    """Delete attendance record (Admin only)"""
    handle_service_error(db, services.delete_attendance, db, attendance_id)
    return None


@router.get("/employees/{employee_id}/summary", response_model=AttendanceSummary)
def get_attendance_summary(
    employee_id: int,
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr", "manager"))
):
    """Get attendance summary for an employee (Admin/HR/Manager only)"""
    try:
        return services.get_attendance_summary(db, employee_id, year, month)
    except services.NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# Leave Request Endpoints (Employee accessible)
@router.post("/leaves", response_model=LeaveRequestOut, status_code=status.HTTP_201_CREATED)
def create_leave_request(
    data: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("employee", "admin", "hr"))
):
    """Create a new leave request"""
    # Set employee_id from current user if not provided
    if not data.employee_id and current_user.get("employee_id"):
        data.employee_id = current_user["employee_id"]
    
    return handle_service_error(db, services.create_leave_request, db, data)


@router.get("/my-leaves", response_model=List[LeaveRequestOut])
def get_my_leaves(
    status: Optional[LeaveStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("employee", "admin", "hr"))
):
    """Get current user's leave requests"""
    if not current_user.get("employee_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not an employee")
    
    return services.get_employee_leave_requests(db, current_user["employee_id"], status)


@router.get("/my-leave-balance", response_model=LeaveBalance)
def get_my_leave_balance(
    year: int = Query(default=date.today().year),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("employee", "admin", "hr"))
):
    """Get current user's leave balance"""
    if not current_user.get("employee_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not an employee")
    
    try:
        return services.get_leave_balance(db, current_user["employee_id"], year)
    except services.NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# Admin/HR/Manager leave endpoints
@router.get("/leaves/{leave_id}", response_model=LeaveRequestOut)
def get_leave_request(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr", "manager"))
):
    """Get leave request by ID (Admin/HR/Manager only)"""
    leave = services.get_leave_request(db, leave_id)
    if not leave:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")
    return leave


@router.get("/employees/{employee_id}/leaves", response_model=List[LeaveRequestOut])
def get_employee_leaves(
    employee_id: int,
    status: Optional[LeaveStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr", "manager"))
):
    """Get leave requests for an employee (Admin/HR/Manager only)"""
    return services.get_employee_leave_requests(db, employee_id, status)


@router.get("/leaves/pending", response_model=List[LeaveRequestOut])
def get_pending_leaves(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr", "manager"))
):
    """Get all pending leave requests (Admin/HR/Manager only)"""
    return services.get_pending_leave_requests(db)


@router.put("/leaves/{leave_id}/approve", response_model=LeaveRequestOut)
def approve_leave(
    leave_id: int,
    decision: LeaveRequestApprove,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr", "manager"))
):
    """Approve or reject a leave request (Admin/HR/Manager only)"""
    return handle_service_error(
        db, services.approve_leave_request, db, leave_id, current_user["id"], decision
    )


@router.put("/leaves/{leave_id}", response_model=LeaveRequestOut)
def update_leave_request(
    leave_id: int,
    updates: LeaveRequestUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr"))
):
    """Update leave request (Admin/HR only)"""
    return handle_service_error(db, services.update_leave_request, db, leave_id, updates)


@router.delete("/leaves/{leave_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_leave_request(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr"))
):
    """Cancel leave request (Admin/HR only)"""
    handle_service_error(db, services.cancel_leave_request, db, leave_id)
    return None


@router.get("/employees/{employee_id}/leave-balance", response_model=LeaveBalance)
def get_leave_balance(
    employee_id: int,
    year: int = Query(default=date.today().year),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr", "manager"))
):
    """Get leave balance for an employee (Admin/HR/Manager only)"""
    try:
        return services.get_leave_balance(db, employee_id, year)
    except services.NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# Holiday Endpoints (Admin/HR only)
@router.post("/holidays", response_model=HolidayOut, status_code=status.HTTP_201_CREATED)
def create_holiday(
    data: HolidayCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr"))
):
    """Create a new holiday (Admin/HR only)"""
    return handle_service_error(db, services.create_holiday, db, data)


@router.get("/holidays/{holiday_id}", response_model=HolidayOut)
def get_holiday(
    holiday_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr", "employee"))
):
    """Get holiday by ID (All authenticated users)"""
    holiday = services.get_holiday(db, holiday_id)
    if not holiday:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holiday not found")
    return holiday


@router.get("/holidays", response_model=List[HolidayOut])
def get_holidays(
    year: int = Query(default=date.today().year),
    location: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr", "employee"))
):
    """Get all holidays for a specific year (All authenticated users)"""
    return services.get_holidays_by_year(db, year, location)


@router.put("/holidays/{holiday_id}", response_model=HolidayOut)
def update_holiday(
    holiday_id: int,
    updates: HolidayUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr"))
):
    """Update holiday (Admin/HR only)"""
    return handle_service_error(db, services.update_holiday, db, holiday_id, updates)


@router.delete("/holidays/{holiday_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holiday(
    holiday_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin"))
):
    """Delete holiday (Admin only)"""
    handle_service_error(db, services.delete_holiday, db, holiday_id)
    return None


# Work Shift Endpoints (Admin/HR only)
@router.post("/shifts", response_model=WorkShiftOut, status_code=status.HTTP_201_CREATED)
def create_work_shift(
    data: WorkShiftCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr"))
):
    """Create a new work shift (Admin/HR only)"""
    return handle_service_error(db, services.create_work_shift, db, data)


@router.get("/shifts/{shift_id}", response_model=WorkShiftOut)
def get_work_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr", "employee"))
):
    """Get work shift by ID (All authenticated users)"""
    shift = services.get_work_shift(db, shift_id)
    if not shift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work shift not found")
    return shift


@router.get("/shifts", response_model=List[WorkShiftOut])
def get_all_work_shifts(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr", "employee"))
):
    """Get all work shifts (All authenticated users)"""
    return services.get_all_work_shifts(db, active_only)


@router.put("/shifts/{shift_id}", response_model=WorkShiftOut)
def update_work_shift(
    shift_id: int,
    updates: WorkShiftUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr"))
):
    """Update work shift (Admin/HR only)"""
    return handle_service_error(db, services.update_work_shift, db, shift_id, updates)


@router.delete("/shifts/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin"))
):
    """Delete work shift (Admin only)"""
    handle_service_error(db, services.delete_work_shift, db, shift_id)
    return None


# Employee Shift Assignment Endpoints (Admin/HR only)
@router.post("/employee-shifts", response_model=EmployeeShiftOut)
def assign_shift_to_employee(
    data: EmployeeShiftAssign,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr"))
):
    """Assign a shift to an employee (Admin/HR only)"""
    return handle_service_error(db, services.assign_shift_to_employee, db, data)


@router.get("/employees/{employee_id}/current-shift", response_model=Optional[EmployeeShiftOut])
def get_employee_current_shift(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr", "manager"))
):
    """Get current shift assignment for an employee (Admin/HR/Manager only)"""
    return services.get_employee_current_shift(db, employee_id)


@router.get("/employees/{employee_id}/shift-history", response_model=List[EmployeeShiftOut])
def get_employee_shift_history(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr", "manager"))
):
    """Get shift assignment history for an employee (Admin/HR/Manager only)"""
    return services.get_employee_shift_history(db, employee_id)


@router.get("/my-current-shift", response_model=Optional[EmployeeShiftOut])
def get_my_current_shift(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("employee", "admin", "hr"))
):
    """Get current user's shift assignment"""
    if not current_user.get("employee_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not an employee")
    
    return services.get_employee_current_shift(db, current_user["employee_id"])


@router.get("/my-shift-history", response_model=List[EmployeeShiftOut])
def get_my_shift_history(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("employee", "admin", "hr"))
):
    """Get current user's shift assignment history"""
    if not current_user.get("employee_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not an employee")
    
    return services.get_employee_shift_history(db, current_user["employee_id"])


@router.put("/employee-shifts/{assignment_id}/end", response_model=EmployeeShiftOut)
def end_shift_assignment(
    assignment_id: int,
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "hr"))
):
    """End a shift assignment (Admin/HR only)"""
    return handle_service_error(db, services.end_shift_assignment, db, assignment_id, end_date)