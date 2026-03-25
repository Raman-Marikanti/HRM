# app/modules/attendance/models.py
from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Boolean, Time, Index, Text
from sqlalchemy.orm import backref, relationship
from datetime import datetime
from app.core.database import Base

class Attendance(Base):
    __tablename__ = "attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    check_in_time = Column(DateTime, nullable=True)
    check_out_time = Column(DateTime, nullable=True)
    check_in_ip = Column(String(45), nullable=True)  # IPv6 support
    check_out_ip = Column(String(45), nullable=True)
    check_in_device = Column(String(255), nullable=True)
    check_out_device = Column(String(255), nullable=True)
    check_in_location = Column(String(255), nullable=True)
    check_out_location = Column(String(255), nullable=True)
    working_hours = Column(String(10), nullable=True)  # Format: "HH:MM:SS"
    status = Column(String(20), default="present", nullable=False)  # present, absent, half-day, late
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes for better performance
    __table_args__ = (
        Index('idx_attendance_employee_date', 'employee_id', 'date'),
        Index('idx_attendance_date_status', 'date', 'status'),
    )
    
    # Relationships
    employee = relationship("Employee", backref=backref("attendance_records", lazy="dynamic"))
    
    @property
    def is_checked_in(self):
        return self.check_in_time is not None
    
    @property
    def is_checked_out(self):
        return self.check_out_time is not None
    
    @property
    def duration(self):
        if self.check_in_time and self.check_out_time:
            duration = self.check_out_time - self.check_in_time
            hours = duration.total_seconds() // 3600
            minutes = (duration.total_seconds() % 3600) // 60
            return f"{int(hours):02d}:{int(minutes):02d}:00"
        return None


class AttendanceSetting(Base):
    __tablename__ = "attendance_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=True)  # For multi-tenant support
    office_start_time = Column(Time, nullable=False, default="09:00:00")
    office_end_time = Column(Time, nullable=False, default="18:00:00")
    late_threshold_minutes = Column(Integer, default=15)  # Minutes after start time considered late
    half_day_threshold_hours = Column(Integer, default=4)  # Hours worked considered half-day
    allow_remote_checkin = Column(Boolean, default=True)
    allow_multiple_checkins = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @property
    def office_start_time_str(self):
        return self.office_start_time.strftime("%H:%M:%S") if self.office_start_time else None
    
    @property
    def office_end_time_str(self):
        return self.office_end_time.strftime("%H:%M:%S") if self.office_end_time else None


class AttendanceImport(Base):
    __tablename__ = "attendance_imports"
    
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    total_records = Column(Integer, default=0)
    successful_records = Column(Integer, default=0)
    failed_records = Column(Integer, default=0)
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    error_log = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    creator = relationship("User", backref="attendance_imports")