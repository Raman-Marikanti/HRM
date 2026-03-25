from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db

from app.modules.admin.schemas import LoginResponse, OTPRequest, OTPResponse, OTPVerify
from app.modules.admin.security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token

from app.modules.admin import services as admin_services

routers = APIRouter(prefix="/employee/auth", tags=["Employee Management"])


# ============================================================================
# OTP Authentication Endpoints
# ============================================================================

@routers.post("/send-otp", response_model=OTPResponse)
def send_otp(
    otp_request: OTPRequest,
    db: Session = Depends(get_db)
):
    """Send OTP to phone number for login/registration"""
    # verify user exists or create a new one (without committing yet)
    User = admin_services.get_user_by_phone(db, otp_request.phone_number)
    if not User:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found. Please register first.")
    if User.employee_code == 'admin':
        return OTPResponse(
            ok=True,
            message="OTP sent successfully (admin user)",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    result = admin_services.send_otp(
        otp_request.phone_number, 
        otp_request.purpose
    )
    return OTPResponse(  
        ok=True,
        message=result["message"],
        expires_in=result["expires_in"]
    )


@routers.post("/verify-otp", response_model=LoginResponse)
def verify_otp_and_login(
    otp_verify: OTPVerify,
    request: Request,
    db: Session = Depends(get_db)
):
    """Verify OTP and login/register user"""
    try:
        # Authenticate with OTP
        auth_result = admin_services.authenticate_with_otp(
            db, 
            otp_verify.phone_number, 
            otp_verify.otp,
            request.client.host
        )
        
        user = auth_result["user"]
        is_new_user = auth_result["is_new_user"]
        
        # Create access token
        access_token = create_access_token(
            subject=user.phone_number,
            extra_data={
                "user_id": user.id,
                "roles":  [user.role]
            }
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user,
            is_new_user=is_new_user
        )
        
    except services.InvalidOTPError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except services.AccountLockedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@routers.post("/logout")
def logout():
    """Logout user (client should discard token)"""
    return {"message": "Successfully logged out"}



# ============================================================================
# EMPLOYEE ENDPOINTS
# ============================================================================

# app/modules/employee/routes.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional, List
from datetime import datetime
from app.core.database import get_db
from app.modules.employee import models, schemas, services
from app.modules.admin.models import User

router = APIRouter(prefix="/employee", tags=["Employee Management"])

# ==================== Department Routes ====================
@router.post("/departments", response_model=schemas.DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    department_in: schemas.DepartmentCreate,
    db: Session = Depends(get_db),
):
    """Create a new department"""
    # Check if department exists
    existing = db.query(models.Department).filter(
        models.Department.name == department_in.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department with this name already exists"
        )
    
    # Create department
    db_department = models.Department(**department_in.model_dump())
    db.add(db_department)
    db.commit()
    db.refresh(db_department)
    
    return db_department

@router.get("/departments", response_model=List[schemas.DepartmentResponse])
def read_departments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get all departments"""
    departments = db.query(models.Department).offset(skip).limit(limit).all()
    return departments

@router.get("/departments/{department_id}", response_model=schemas.DepartmentResponse)
def read_department(
    department_id: int,
    db: Session = Depends(get_db),
):
    """Get department by ID"""
    department = db.query(models.Department).filter(
        models.Department.id == department_id
    ).first()
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    return department

@router.put("/departments/{department_id}", response_model=schemas.DepartmentResponse)
def update_department(
    department_id: int,
    department_in: schemas.DepartmentUpdate,
    db: Session = Depends(get_db),
):
    """Update department"""
    department = db.query(models.Department).filter(
        models.Department.id == department_id
    ).first()
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    # Update fields
    update_data = department_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(department, field, value)
    
    db.add(department)
    db.commit()
    db.refresh(department)
    
    return department

@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
):
    """Delete department"""
    department = db.query(models.Department).filter(
        models.Department.id == department_id
    ).first()
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    db.delete(department)
    db.commit()
    
    return None

# ==================== Designation Routes ====================
@router.post("/designations", response_model=schemas.DesignationResponse, status_code=status.HTTP_201_CREATED)
def create_designation(
    designation_in: schemas.DesignationCreate,
    db: Session = Depends(get_db),
):
    """Create a new designation"""
    # Check if designation exists
    existing = db.query(models.Designation).filter(
        models.Designation.title == designation_in.title
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Designation with this title already exists"
        )
    
    # Create designation
    db_designation = models.Designation(**designation_in.model_dump())
    db.add(db_designation)
    db.commit()
    db.refresh(db_designation)
    
    return db_designation

@router.get("/designations", response_model=List[schemas.DesignationResponse])
def read_designations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get all designations"""
    designations = db.query(models.Designation).offset(skip).limit(limit).all()
    return designations

@router.get("/designations/{designation_id}", response_model=schemas.DesignationResponse)
def read_designation(
    designation_id: int,
    db: Session = Depends(get_db),
):
    """Get designation by ID"""
    designation = db.query(models.Designation).filter(
        models.Designation.id == designation_id
    ).first()
    
    if not designation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Designation not found"
        )
    return designation

@router.put("/designations/{designation_id}", response_model=schemas.DesignationResponse)
def update_designation(
    designation_id: int,
    designation_in: schemas.DesignationUpdate,
    db: Session = Depends(get_db),
):
    """Update designation"""
    designation = db.query(models.Designation).filter(
        models.Designation.id == designation_id
    ).first()
    
    if not designation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Designation not found"
        )
    
    # Update fields
    update_data = designation_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(designation, field, value)
    
    db.add(designation)
    db.commit()
    db.refresh(designation)
    
    return designation

@router.delete("/designations/{designation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_designation(
    designation_id: int,
    db: Session = Depends(get_db),
):
    """Delete designation"""
    designation = db.query(models.Designation).filter(
        models.Designation.id == designation_id
    ).first()
    
    if not designation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Designation not found"
        )
    
    db.delete(designation)
    db.commit()
    
    return None

# ==================== Employee Routes ====================
@router.post("/employees", response_model=schemas.EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    employee_in: schemas.EmployeeCreate,
    db: Session = Depends(get_db),
):
    """Create a new employee with all details"""
    

    
    # Check if user exists and doesn't have employee record
    user = db.query(User).filter(User.id == employee_in.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    employee_in.employee_code = user.employee_code

    
    # Create employee
    employee_data = employee_in.model_dump(exclude={
        'bank_detail', 'employee_personal_detail', 
        'employee_document_detail', 'employee_profile'
    })
    db_employee = models.Employee(**employee_data)
    db.add(db_employee)
    db.flush()  # Get employee ID
    
    # Create bank detail
    if employee_in.bank_detail:
        bank_detail_data = employee_in.bank_detail.model_dump()
        db_bank_detail = models.BankDetail(**bank_detail_data, employee_id=db_employee.id)
        db.add(db_bank_detail)
    
    # Create personal detail
    if employee_in.employee_personal_detail:
        personal_detail_data = employee_in.employee_personal_detail.model_dump()
        db_personal_detail = models.EmployeePersonalDetail(
            **personal_detail_data, 
            employee_id=db_employee.id
        )
        db.add(db_personal_detail)
    
    # Create document detail
    if employee_in.employee_document_detail:
        document_detail_data = employee_in.employee_document_detail.model_dump()
        db_document_detail = models.EmployeeDocumentDetail(
            **document_detail_data, 
            employee_id=db_employee.id
        )
        db.add(db_document_detail)
    
    # Create profile
    if employee_in.employee_profile:
        profile_data = employee_in.employee_profile.model_dump()
        db_profile = models.EmployeeProfile(
            **profile_data, 
            employee_id=db_employee.id
        )
        db.add(db_profile)
    
    db.commit()
    db.refresh(db_employee)
    
    return db_employee

@router.put("/employees/{employee_id}", response_model=schemas.EmployeeResponse)
def update_employee(
    employee_id: int,
    employee_in: schemas.EmployeeUpdate,
    db: Session = Depends(get_db),
):
    """Update employee details"""
    employee = db.query(models.Employee).filter(
        models.Employee.id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Update employee fields
    update_data = employee_in.model_dump(exclude_unset=True, exclude={
        'bank_detail', 'employee_personal_detail', 
        'employee_document_detail', 'employee_profile'
    })
    
    for field, value in update_data.items():
        setattr(employee, field, value)
    
    # Update bank detail
    if employee_in.bank_detail:
        if employee.bank_detail:
            for field, value in employee_in.bank_detail.model_dump(exclude_unset=True).items():
                setattr(employee.bank_detail, field, value)
        else:
            bank_detail_data = employee_in.bank_detail.model_dump()
            db_bank_detail = models.BankDetail(**bank_detail_data, employee_id=employee.id)
            db.add(db_bank_detail)
    
    # Update personal detail
    if employee_in.employee_personal_detail:
        if employee.employee_personal_detail:
            for field, value in employee_in.employee_personal_detail.model_dump(exclude_unset=True).items():
                setattr(employee.employee_personal_detail, field, value)
        else:
            personal_detail_data = employee_in.employee_personal_detail.model_dump()
            db_personal_detail = models.EmployeePersonalDetail(
                **personal_detail_data, 
                employee_id=employee.id
            )
            db.add(db_personal_detail)
    
    # Update document detail
    if employee_in.employee_document_detail:
        if employee.employee_document_detail:
            for field, value in employee_in.employee_document_detail.model_dump(exclude_unset=True).items():
                setattr(employee.employee_document_detail, field, value)
        else:
            document_detail_data = employee_in.employee_document_detail.model_dump()
            db_document_detail = models.EmployeeDocumentDetail(
                **document_detail_data, 
                employee_id=employee.id
            )
            db.add(db_document_detail)
    
    # Update profile
    if employee_in.employee_profile:
        if employee.employee_profile:
            for field, value in employee_in.employee_profile.model_dump(exclude_unset=True).items():
                setattr(employee.employee_profile, field, value)
        else:
            profile_data = employee_in.employee_profile.model_dump()
            db_profile = models.EmployeeProfile(
                **profile_data,
                employee_id=employee.id
            )
            db.add(db_profile)

    db.commit()
    db.refresh(employee)

    return employee


@router.get("/employees", response_model=List[schemas.EmployeeListResponse])
def read_employees(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    department_id: Optional[int] = Query(None),
    designation_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, min_length=1),
    db: Session = Depends(get_db),
):
    """Get all employees with filters"""
    
    query = db.query(models.Employee)
    
    # Apply filters
    if department_id:
        query = query.filter(models.Employee.department_id == department_id)
    
    if designation_id:
        query = query.filter(models.Employee.designation_id == designation_id)
    
    if is_active is not None:
        query = query.filter(models.Employee.is_active == is_active)
    
    if search:
        query = query.join(models.User).filter(
            or_(
                models.User.first_name.ilike(f"%{search}%"),
                models.User.last_name.ilike(f"%{search}%"),
                models.Employee.employee_code.ilike(f"%{search}%")
            )
        )
    
    employees = query.offset(skip).limit(limit).all()
    
    return employees

@router.get("/employees/{user_id}", response_model=schemas.EmployeeResponse)
def read_employee(
    user_id: int,
    db: Session = Depends(get_db),
):
    """Get employee by ID with all details"""
    
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user_id
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    return employee

@router.get("/employees/by-code/{employee_code}", response_model=schemas.EmployeeResponse)
def read_employee_by_code(
    employee_code: str,
    db: Session = Depends(get_db),
):
    """Get employee by employee code"""
    
    employee = db.query(models.Employee).filter(
        models.Employee.employee_code == employee_code
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    return employee

@router.put("/employees/{user_id}", response_model=schemas.EmployeeResponse)
def update_employee(
    user_id: int,
    employee_in: schemas.EmployeeUpdate,
    db: Session = Depends(get_db),
):
    """Update employee details"""
    
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user_id
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Update employee fields
    update_data = employee_in.model_dump(exclude_unset=True, exclude={
        'bank_detail', 'employee_personal_detail', 
        'employee_document_detail', 'employee_profile'
    })
    
    for field, value in update_data.items():
        setattr(employee, field, value)
    
    # Update bank detail
    if employee_in.bank_detail:
        if employee.bank_detail:
            for field, value in employee_in.bank_detail.model_dump(exclude_unset=True).items():
                setattr(employee.bank_detail, field, value)
        else:
            bank_detail_data = employee_in.bank_detail.model_dump()
            db_bank_detail = models.BankDetail(**bank_detail_data, employee_id=employee.id)
            db.add(db_bank_detail)
    
    # Update personal detail
    if employee_in.employee_personal_detail:
        if employee.employee_personal_detail:
            for field, value in employee_in.employee_personal_detail.model_dump(exclude_unset=True).items():
                setattr(employee.employee_personal_detail, field, value)
        else:
            personal_detail_data = employee_in.employee_personal_detail.model_dump()
            db_personal_detail = models.EmployeePersonalDetail(
                **personal_detail_data, 
                employee_id=employee.id
            )
            db.add(db_personal_detail)
    
    # Update document detail
    if employee_in.employee_document_detail:
        if employee.employee_document_detail:
            for field, value in employee_in.employee_document_detail.model_dump(exclude_unset=True).items():
                setattr(employee.employee_document_detail, field, value)
        else:
            document_detail_data = employee_in.employee_document_detail.model_dump()
            db_document_detail = models.EmployeeDocumentDetail(
                **document_detail_data, 
                employee_id=employee.id
            )
            db.add(db_document_detail)
    
    # Update profile
    if employee_in.employee_profile:
        if employee.employee_profile:
            for field, value in employee_in.employee_profile.model_dump(exclude_unset=True).items():
                setattr(employee.employee_profile, field, value)
        else:
            profile_data = employee_in.employee_profile.model_dump()
            db_profile = models.EmployeeProfile(
                **profile_data, 
                employee_id=employee.id
            )
            db.add(db_profile)
    
    db.add(employee)
    db.commit()
    db.refresh(employee)
    
    return employee

@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
):
    """Delete employee (CASCADE will delete related records)"""
    
    employee = db.query(models.Employee).filter(
        models.Employee.id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    db.delete(employee)
    db.commit()
    
    return None

# ==================== Employee Statistics Routes ====================
@router.get("/statistics/dashboard")
def get_employee_statistics(
    db: Session = Depends(get_db),
):
    """Get employee statistics for dashboard"""
    
    total_employees = db.query(models.Employee).count()
    active_employees = db.query(models.Employee).filter(
        models.Employee.is_active == True
    ).count()
    
    # Department wise count
    departments = db.query(models.Department).all()
    dept_stats = []
    for dept in departments:
        count = db.query(models.Employee).filter(
            models.Employee.department_id == dept.id
        ).count()
        dept_stats.append({
            "department_id": dept.id,
            "department_name": dept.name,
            "employee_count": count
        })
    
    # Designation wise count
    designations = db.query(models.Designation).all()
    desig_stats = []
    for desig in designations:
        count = db.query(models.Employee).filter(
            models.Employee.designation_id == desig.id
        ).count()
        desig_stats.append({
            "designation_id": desig.id,
            "designation_title": desig.title,
            "employee_count": count
        })
    
    return {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "inactive_employees": total_employees - active_employees,
        "department_wise": dept_stats,
        "designation_wise": desig_stats
    }

# ==================== Organization Hierarchy Routes ====================
@router.get("/hierarchy/{employee_id}")
def get_employee_hierarchy(
    employee_id: int,
    db: Session = Depends(get_db),
):
    """Get employee reporting hierarchy"""
    
    employee = db.query(models.Employee).filter(
        models.Employee.id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    hierarchy = []
    current = employee
    
    while current.manager:
        hierarchy.append({
            "id": current.manager.id,
            "name": current.manager.full_name,
            "employee_code": current.manager.employee_code,
            "designation": current.manager.designation.title if current.manager.designation else None,
            "department": current.manager.department.name if current.manager.department else None
        })
        current = current.manager
    
    # Get subordinates
    subordinates = db.query(models.Employee).filter(
        models.Employee.manager_id == employee_id
    ).all()
    
    subordinate_list = []
    for sub in subordinates:
        subordinate_list.append({
            "id": sub.id,
            "name": sub.full_name,
            "employee_code": sub.employee_code,
            "designation": sub.designation.title if sub.designation else None,
            "department": sub.department.name if sub.department else None
        })
    
    return {
        "employee": {
            "id": employee.id,
            "name": employee.full_name,
            "employee_code": employee.employee_code,
            "designation": employee.designation.title if employee.designation else None,
            "department": employee.department.name if employee.department else None
        },
        "reporting_chain": hierarchy,
        "subordinates": subordinate_list
    }

# ==================== Bulk Operations Routes ====================
@router.post("/employees/bulk", response_model=List[schemas.EmployeeResponse], status_code=status.HTTP_201_CREATED)
def create_employees_bulk(
    employees_in: List[schemas.EmployeeCreate],
    db: Session = Depends(get_db),
):
    """Create multiple employees in bulk"""
    
    created_employees = []
    errors = []
    
    for idx, employee_in in enumerate(employees_in):
        try:
            # Check if employee code exists
            existing = db.query(models.Employee).filter(
                models.Employee.employee_code == employee_in.employee_code
            ).first()
            if existing:
                errors.append({
                    "index": idx,
                    "employee_code": employee_in.employee_code,
                    "error": "Employee code already exists"
                })
                continue
            
            # Check if user exists
            user = db.query(User).filter(User.id == employee_in.user_id).first()
            if not user:
                errors.append({
                    "index": idx,
                    "employee_code": employee_in.employee_code,
                    "error": "User not found"
                })
                continue
            
            # Create employee
            employee_data = employee_in.model_dump(exclude={
                'bank_detail', 'employee_personal_detail', 
                'employee_document_detail', 'employee_profile'
            })
            db_employee = models.Employee(**employee_data)
            db.add(db_employee)
            db.flush()
            
            # Create related details
            if employee_in.bank_detail:
                db_bank = models.BankDetail(**employee_in.bank_detail.model_dump(), employee_id=db_employee.id)
                db.add(db_bank)
            
            if employee_in.employee_personal_detail:
                db_personal = models.EmployeePersonalDetail(
                    **employee_in.employee_personal_detail.model_dump(), 
                    employee_id=db_employee.id
                )
                db.add(db_personal)
            
            if employee_in.employee_document_detail:
                db_doc = models.EmployeeDocumentDetail(
                    **employee_in.employee_document_detail.model_dump(), 
                    employee_id=db_employee.id
                )
                db.add(db_doc)
            
            if employee_in.employee_profile:
                db_profile = models.EmployeeProfile(
                    **employee_in.employee_profile.model_dump(), 
                    employee_id=db_employee.id
                )
                db.add(db_profile)
            
            created_employees.append(db_employee)
            
        except Exception as e:
            errors.append({
                "index": idx,
                "employee_code": employee_in.employee_code,
                "error": str(e)
            })
    
    db.commit()
    
    # Refresh all created employees
    for employee in created_employees:
        db.refresh(employee)
    
    if errors:
        raise HTTPException(
            status_code=status.HTTP_207_MULTI_STATUS,
            detail={
                "message": "Bulk operation completed with errors",
                "created": len(created_employees),
                "errors": errors
            }
        )
    
    return created_employees

# ==================== Export Routes ====================
@router.get("/export/employees")
def export_employees(
    format: str = Query("json", regex="^(json|csv)$"),
    department_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Export employee data in JSON or CSV format"""
    
    query = db.query(models.Employee)
    
    if department_id:
        query = query.filter(models.Employee.department_id == department_id)
    
    employees = query.all()
    
    export_data = []
    for emp in employees:
        export_data.append({
            "employee_code": emp.employee_code,
            "full_name": emp.full_name,
            "email": emp.user.email if emp.user else None,
            "department": emp.department.name if emp.department else None,
            "designation": emp.designation.title if emp.designation else None,
            "date_of_joining": emp.date_of_joining,
            "is_active": emp.is_active,
            "bank_account": emp.bank_detail.bank_account_number if emp.bank_detail else None,
            "pan_number": emp.employee_document_detail.pancard_number if emp.employee_document_detail else None,
            "aadhar_number": emp.employee_document_detail.aadhar_number if emp.employee_document_detail else None
        })
    
    if format == "csv":
        import csv
        from fastapi.responses import StreamingResponse
        import io
        
        output = io.StringIO()
        if export_data:
            writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
            writer.writeheader()
            writer.writerows(export_data)
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=employees_export.csv"}
        )
    
    return export_data