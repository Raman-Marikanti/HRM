# app/modules/attendance/routes.py
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import Optional, List
from datetime import datetime, date, timedelta, timezone
from app.core.database import get_db
from app.modules.attendance import models, schemas
from app.modules.employee.models import Employee, Department
from app.modules.admin.models import User

import csv
import io
import json

router = APIRouter(prefix="/attendance", tags=["Attendance Management"])

# ==================== Check-In/Check-Out Routes ====================
@router.post("/check-in", response_model=schemas.AttendanceResponse, status_code=status.HTTP_201_CREATED)
def check_in(
    check_in_data: schemas.CheckInRequest,
    db: Session = Depends(get_db)
):
    """Employee check-in"""
    
    # Check if employee exists
    employee = db.query(Employee).filter(Employee.id == check_in_data.employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Get attendance settings
    settings = db.query(models.AttendanceSetting).first()
    if not settings:
        settings = models.AttendanceSetting()
        db.add(settings)
        db.commit()
    
    # Get current date
    current_date = check_in_data.date or datetime.utcnow()
    today = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Check if already checked in today
    existing_attendance = db.query(models.Attendance).filter(
        and_(
            models.Attendance.employee_id == check_in_data.employee_id,
            models.Attendance.date >= today,
            models.Attendance.date < today + timedelta(days=1)
        )
    ).first()
    
    if existing_attendance:
        if existing_attendance.check_in_time and not existing_attendance.is_checked_out:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already checked in today"
            )
    
    # Create attendance record
    attendance = models.Attendance(
        employee_id=check_in_data.employee_id,
        date=current_date,
        check_in_time=current_date,
        check_in_ip=check_in_data.check_in_ip,
        check_in_device=check_in_data.check_in_device,
        check_in_location=check_in_data.check_in_location,
        remarks=check_in_data.remarks
    )
    
    # Determine status based on check-in time
    check_in_time = current_date.time()
    if check_in_time > settings.office_start_time:
        late_minutes = (datetime.combine(date.today(), check_in_time) - 
                       datetime.combine(date.today(), settings.office_start_time)).total_seconds() / 60
        if late_minutes > settings.late_threshold_minutes:
            attendance.status = "late"
    
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    
    return attendance

@router.put("/check-out", response_model=schemas.AttendanceResponse)
def check_out(
    check_out_data: schemas.CheckOutRequest,
    db: Session = Depends(get_db)
):
    """Employee check-out"""
    
    # Check if employee exists
    employee = db.query(Employee).filter(Employee.id == check_out_data.employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Get current date
    current_date = check_out_data.date or datetime.utcnow()
    today = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get today's attendance record
    attendance = db.query(models.Attendance).filter(
        and_(
            models.Attendance.employee_id == check_out_data.employee_id,
            models.Attendance.date >= today,
            models.Attendance.date < today + timedelta(days=1),
            
            
        )
    ).first()
    
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No check-in record found for today"
        )
    
    # if attendance.check_out_time :
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Already checked out"
    #     )
    
    # Update check-out time
    attendance.check_out_time = current_date
    attendance.check_out_ip = check_out_data.check_out_ip
    attendance.check_out_device = check_out_data.check_out_device
    attendance.check_out_location = check_out_data.check_out_location
    if check_out_data.remarks:
        attendance.remarks = check_out_data.remarks
    
    # Calculate working hours
    check_in = attendance.check_in_time
    check_out = attendance.check_out_time

# ✅ make both timezone-aware (UTC)
    if check_in and check_in.tzinfo is None:
        check_in = check_in.replace(tzinfo=timezone.utc)

    if check_out and check_out.tzinfo is None:
        check_out = check_out.replace(tzinfo=timezone.utc)
        
    if attendance.check_in_time:
        duration =check_out - check_in
        hours = duration.total_seconds() // 3600
        minutes = (duration.total_seconds() % 3600) // 60
        attendance.working_hours = f"{int(hours):02d}:{int(minutes):02d}:00"
        
        # Update status based on working hours
        settings = db.query(models.AttendanceSetting).first()
        if settings and hours < settings.half_day_threshold_hours:
            attendance.status = "half-day"
    
    db.commit()
    db.refresh(attendance)
    
    return attendance


@router.get("/today/{employee_id}")
def get_today_attendance(employee_id: int, db: Session = Depends(get_db)):
    """Get today's first check-in, last check-out, and total working hours"""

    # ✅ use timezone-aware
    today = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    records = db.query(models.Attendance).filter(
        and_(
            models.Attendance.employee_id == employee_id,
            models.Attendance.check_in_time >= today,
            models.Attendance.check_in_time < today + timedelta(days=1)
        )
    ).order_by(models.Attendance.check_in_time.asc()).all()

    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No attendance record found for today"
        )

   
    first_check_in = records[0].check_in_time

  
    last_check_out = None
    for r in reversed(records):
        if r.check_out_time:
            last_check_out = r.check_out_time
            break

    total_seconds = 0

    for r in records:
        if r.check_in_time and r.check_out_time:

            check_in = r.check_in_time
            check_out = r.check_out_time

            # 🔥 normalize timezone (avoid your previous error)
            if check_in.tzinfo is None:
                check_in = check_in.replace(tzinfo=timezone.utc)
            if check_out.tzinfo is None:
                check_out = check_out.replace(tzinfo=timezone.utc)

            diff = check_out - check_in
            total_seconds += int(diff.total_seconds())

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    total_working_hours = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

   
    return {
        "employee_id": employee_id,
        "date": today.date(),
        "first_check_in": first_check_in,
        "last_check_out": last_check_out,
        "total_working_hours": total_working_hours,
        "sessions_count": len(records)
    }

# ==================== Attendance Records Routes ====================
@router.get("/records", response_model=List[schemas.AttendanceDetailResponse])
def get_attendance_records(
    employee_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get attendance records with filters"""
    
    query = db.query(models.Attendance)
    
    # Apply filters
    if employee_id:
        query = query.filter(models.Attendance.employee_id == employee_id)
    
    if department_id:
        query = query.join(Employee).filter(Employee.department_id == department_id)
    
    if start_date:
        query = query.filter(models.Attendance.date >= start_date)
    
    if end_date:
        query = query.filter(models.Attendance.date <= end_date)
    
    if status:
        query = query.filter(models.Attendance.status == status)
    
    # Order by date descending
    query = query.order_by(desc(models.Attendance.date))
    
    records = query.offset(skip).limit(limit).all()
    
    # Add employee details
    result = []
    for record in records:
        record_data = schemas.AttendanceDetailResponse.model_validate(record)
        if record.employee:
            record_data.employee_name = record.employee.full_name
            record_data.employee_code = record.employee.employee_code
            if record.employee.department:
                record_data.department = record.employee.department.name
        result.append(record_data)
    
    return result

@router.get("/records/{record_id}", response_model=schemas.AttendanceDetailResponse)
def get_attendance_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    """Get attendance record by ID"""
    
    record = db.query(models.Attendance).filter(models.Attendance.id == record_id).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )
    
    record_data = schemas.AttendanceDetailResponse.model_validate(record)
    if record.employee:
        record_data.employee_name = record.employee.full_name
        record_data.employee_code = record.employee.employee_code
        if record.employee.department:
            record_data.department = record.employee.department.name
    
    return record_data

@router.put("/records/{record_id}", response_model=schemas.AttendanceResponse)
def update_attendance_record(
    record_id: int,
    record_in: schemas.AttendanceUpdate,
    db: Session = Depends(get_db)
):
    """Update attendance record (admin only)"""
    
    record = db.query(models.Attendance).filter(models.Attendance.id == record_id).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )
    
    # Update fields
    update_data = record_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)
    
    # Recalculate working hours if both check-in and check-out are present
    if record.check_in_time and record.check_out_time:
        duration = record.check_out_time - record.check_in_time
        hours = duration.total_seconds() // 3600
        minutes = (duration.total_seconds() % 3600) // 60
        record.working_hours = f"{int(hours):02d}:{int(minutes):02d}:00"
    
    db.commit()
    db.refresh(record)
    
    return record

@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    """Delete attendance record (admin only)"""
    
    record = db.query(models.Attendance).filter(models.Attendance.id == record_id).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )
    
    db.delete(record)
    db.commit()
    
    return None

# ==================== Attendance Settings Routes ====================
@router.get("/settings", response_model=schemas.AttendanceSettingResponse)
def get_attendance_settings(
    db: Session = Depends(get_db)
):
    """Get attendance settings"""
    
    settings = db.query(models.AttendanceSetting).first()
    
    if not settings:
        # Create default settings
        settings = models.AttendanceSetting()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return settings

@router.put("/settings", response_model=schemas.AttendanceSettingResponse)
def update_attendance_settings(
    settings_in: schemas.AttendanceSettingUpdate,
    db: Session = Depends(get_db)
):
    """Update attendance settings"""
    
    settings = db.query(models.AttendanceSetting).first()
    
    if not settings:
        settings = models.AttendanceSetting()
        db.add(settings)
    
    # Update fields
    update_data = settings_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    
    return settings

# ==================== Statistics Routes ====================
@router.get("/statistics/daily")
def get_daily_statistics(
    date: Optional[datetime] = Query(None),
    department_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get daily attendance statistics"""
    
    target_date = date or datetime.utcnow()
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    
    # Get employees
    query = db.query(Employee)
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    
    total_employees = query.count()
    
    # Get attendance records for the day
    attendance_query = db.query(models.Attendance).filter(
        and_(
            models.Attendance.date >= start_of_day,
            models.Attendance.date < end_of_day
        )
    )
    
    if department_id:
        attendance_query = attendance_query.join(Employee).filter(Employee.department_id == department_id)
    
    records = attendance_query.all()
    
    present = len(records)
    late = len([r for r in records if r.status == "late"])
    half_day = len([r for r in records if r.status == "half-day"])
    absent = total_employees - present
    
    attendance_percentage = (present / total_employees * 100) if total_employees > 0 else 0
    
    return {
        "date": start_of_day,
        "total_employees": total_employees,
        "present": present,
        "absent": absent,
        "late": late,
        "half_day": half_day,
        "attendance_percentage": round(attendance_percentage, 2)
    }

@router.get("/statistics/employee/{employee_id}")
def get_employee_statistics(
    employee_id: int,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """Get attendance statistics for an employee"""
    
    # Check if employee exists
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Set date range
    if not start_date:
        start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    if not end_date:
        end_date = datetime.utcnow()
    
    # Get attendance records
    records = db.query(models.Attendance).filter(
        and_(
            models.Attendance.employee_id == employee_id,
            models.Attendance.date >= start_date,
            models.Attendance.date <= end_date
        )
    ).all()
    
    total_days = (end_date - start_date).days + 1
    present_days = len(records)
    late_days = len([r for r in records if r.status == "late"])
    half_days = len([r for r in records if r.status == "half-day"])
    absent_days = total_days - present_days
    
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
    
    return {
        "employee_id": employee_id,
        "employee_name": employee.full_name,
        "employee_code": employee.employee_code,
        "start_date": start_date,
        "end_date": end_date,
        "total_days": total_days,
        "present_days": present_days,
        "absent_days": absent_days,
        "late_days": late_days,
        "half_days": half_days,
        "attendance_percentage": round(attendance_percentage, 2),
        "records": records
    }

@router.get("/statistics/monthly")
def get_monthly_statistics(
    year: int = Query(default=datetime.utcnow().year),
    month: int = Query(default=datetime.utcnow().month),
    department_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get monthly attendance statistics"""
    
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    
    # Get employees
    query = db.query(Employee)
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    
    employees = query.all()
    
    monthly_stats = []
    for employee in employees:
        records = db.query(models.Attendance).filter(
            and_(
                models.Attendance.employee_id == employee.id,
                models.Attendance.date >= start_date,
                models.Attendance.date <= end_date
            )
        ).all()
        
        total_days = (end_date - start_date).days + 1
        present_days = len(records)
        
        monthly_stats.append({
            "employee_id": employee.id,
            "employee_name": employee.full_name,
            "employee_code": employee.employee_code,
            "present_days": present_days,
            "absent_days": total_days - present_days,
            "attendance_percentage": round((present_days / total_days * 100), 2) if total_days > 0 else 0
        })
    
    return {
        "year": year,
        "month": month,
        "start_date": start_date,
        "end_date": end_date,
        "total_employees": len(employees),
        "monthly_stats": monthly_stats
    }

# ==================== Bulk Import Routes ====================
@router.post("/import/csv", response_model=schemas.AttendanceImportResponse)
async def import_attendance_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Import attendance records from CSV file"""
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are allowed"
        )
    
    # Create import record
    import_record = models.AttendanceImport(
        file_name=file.filename,
        file_path=f"uploads/{file.filename}",
        created_by=current_user.id,
        status="processing"
    )
    db.add(import_record)
    db.commit()
    db.refresh(import_record)
    
    try:
        # Read CSV content
        content = await file.read()
        csv_data = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        
        successful = 0
        failed = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Extract data from CSV
                employee_code = row.get('employee_code')
                date_str = row.get('date')
                check_in_str = row.get('check_in_time')
                check_out_str = row.get('check_out_time')
                
                # Find employee
                employee = db.query(Employee).filter(Employee.employee_code == employee_code).first()
                if not employee:
                    errors.append(f"Row {row_num}: Employee {employee_code} not found")
                    failed += 1
                    continue
                
                # Parse date and times
                date = parser.parse(date_str) if date_str else None
                check_in_time = parser.parse(check_in_str) if check_in_str else None
                check_out_time = parser.parse(check_out_str) if check_out_str else None
                
                if not date:
                    errors.append(f"Row {row_num}: Date is required")
                    failed += 1
                    continue
                
                # Create attendance record
                attendance = models.Attendance(
                    employee_id=employee.id,
                    date=date,
                    check_in_time=check_in_time,
                    check_out_time=check_out_time,
                    status=row.get('status', 'present'),
                    remarks=row.get('remarks')
                )
                
                # Calculate working hours if both times present
                if check_in_time and check_out_time:
                    duration = check_out_time - check_in_time
                    hours = duration.total_seconds() // 3600
                    minutes = (duration.total_seconds() % 3600) // 60
                    attendance.working_hours = f"{int(hours):02d}:{int(minutes):02d}:00"
                
                db.add(attendance)
                successful += 1
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                failed += 1
        
        # Commit all records
        db.commit()
        
        # Update import record
        import_record.total_records = successful + failed
        import_record.successful_records = successful
        import_record.failed_records = failed
        import_record.status = "completed"
        import_record.error_log = "\n".join(errors) if errors else None
        db.commit()
        
        return schemas.AttendanceImportResponse(
            import_id=import_record.id,
            status="completed",
            total_records=import_record.total_records,
            successful_records=successful,
            failed_records=failed,
            error_log=import_record.error_log
        )
        
    except Exception as e:
        import_record.status = "failed"
        import_record.error_log = str(e)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )

# ==================== Export Routes ====================
@router.get("/export")
def export_attendance(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    department_id: Optional[int] = Query(None),
    format: str = Query("json", regex="^(json|csv)$"),
    db: Session = Depends(get_db)
):
    """Export attendance records"""
    
    query = db.query(models.Attendance)
    
    if start_date:
        query = query.filter(models.Attendance.date >= start_date)
    
    if end_date:
        query = query.filter(models.Attendance.date <= end_date)
    
    if department_id:
        query = query.join(Employee).filter(Employee.department_id == department_id)
    
    records = query.all()
    
    export_data = []
    for record in records:
        export_data.append({
            "employee_code": record.employee.employee_code if record.employee else None,
            "employee_name": record.employee.full_name if record.employee else None,
            "department": record.employee.department.name if record.employee and record.employee.department else None,
            "date": record.date,
            "check_in_time": record.check_in_time,
            "check_out_time": record.check_out_time,
            "working_hours": record.working_hours,
            "status": record.status,
            "remarks": record.remarks
        })
    
    if format == "csv":
        import csv
        from fastapi.responses import StreamingResponse
        
        output = io.StringIO()
        if export_data:
            writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
            writer.writeheader()
            writer.writerows(export_data)
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=attendance_export.csv"}
        )
    
    return export_data