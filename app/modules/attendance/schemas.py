# app/modules/attendance/schemas.py
from datetime import datetime, time
from typing import Optional, List
from pydantic import BaseModel, Field, validator, field_validator

# Attendance Schemas
class AttendanceBase(BaseModel):
    date: datetime
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    check_in_ip: Optional[str] = Field(None, max_length=45)
    check_out_ip: Optional[str] = Field(None, max_length=45)
    check_in_device: Optional[str] = Field(None, max_length=255)
    check_out_device: Optional[str] = Field(None, max_length=255)
    check_in_location: Optional[str] = Field(None, max_length=255)
    check_out_location: Optional[str] = Field(None, max_length=255)
    remarks: Optional[str] = None

class CheckInRequest(BaseModel):
    user_id: int
    check_in_ip: Optional[str] = Field(None, max_length=45)
    check_in_device: Optional[str] = Field(None, max_length=255)
    check_in_location: Optional[str] = Field(None, max_length=255)
    date: Optional[datetime] = None  # For manual check-in, defaults to current time
    remarks: Optional[str] = None

class CheckOutRequest(BaseModel):
    user_id: int
    check_out_ip: Optional[str] = Field(None, max_length=45)
    check_out_device: Optional[str] = Field(None, max_length=255)
    check_out_location: Optional[str] = Field(None, max_length=255)
    date: Optional[datetime] = None  # For manual check-out, defaults to current time
    remarks: Optional[str] = None

class AttendanceCreate(AttendanceBase):
    user_id: int
    status: Optional[str] = "present"

class AttendanceUpdate(BaseModel):
    check_out_time: Optional[datetime] = None
    check_in_ip: Optional[str] = None
    check_out_ip: Optional[str] = None
    check_in_device: Optional[str] = None
    check_out_device: Optional[str] = None
    check_in_location: Optional[str] = None
    check_out_location: Optional[str] = None
    status: Optional[str] = None
    remarks: Optional[str] = None

class AttendanceResponse(AttendanceBase):
    id: int
    employee_id: int
    working_hours: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AttendanceDetailResponse(AttendanceResponse):
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    department: Optional[str] = None
    
    class Config:
        from_attributes = True

# Attendance Setting Schemas
class AttendanceSettingBase(BaseModel):
    office_start_time: time = Field(default="09:00:00")
    office_end_time: time = Field(default="18:00:00")
    late_threshold_minutes: int = Field(default=15, ge=0, le=120)
    half_day_threshold_hours: int = Field(default=4, ge=1, le=8)
    allow_remote_checkin: bool = True
    allow_multiple_checkins: bool = False
    company_id: Optional[int] = None

class AttendanceSettingCreate(AttendanceSettingBase):
    pass

class AttendanceSettingUpdate(BaseModel):
    office_start_time: Optional[time] = None
    office_end_time: Optional[time] = None
    late_threshold_minutes: Optional[int] = Field(None, ge=0, le=120)
    half_day_threshold_hours: Optional[int] = Field(None, ge=1, le=8)
    allow_remote_checkin: Optional[bool] = None
    allow_multiple_checkins: Optional[bool] = None

class AttendanceSettingResponse(AttendanceSettingBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Attendance Statistics
class DailyAttendanceStats(BaseModel):
    date: datetime
    total_employees: int
    present: int
    absent: int
    late: int
    half_day: int
    attendance_percentage: float

class EmployeeAttendanceStats(BaseModel):
    user_id: int
    employee_name: str
    employee_code: str
    total_days: int
    present_days: int
    absent_days: int
    late_days: int
    half_days: int
    attendance_percentage: float

# Bulk Import Schemas
class AttendanceImportRequest(BaseModel):
    file_name: str
    file_content: str  # Base64 encoded file content

class AttendanceImportResponse(BaseModel):
    import_id: int
    status: str
    total_records: int
    successful_records: int
    failed_records: int
    error_log: Optional[str] = None

# Query Filters
class AttendanceFilter(BaseModel):
    user_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None
    department_id: Optional[int] = None
    is_checked_in: Optional[bool] = None
    is_checked_out: Optional[bool] = None