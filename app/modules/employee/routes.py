from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import require_roles, get_current_user
from app.core.errors import (
    ResourceNotFoundError, ValidationError, DuplicateError, 
    ErrorCodes, HRMSException
)
from app.core.utils import (
    ResponseFormatter, AuditLogger, RequestContextManager
)
from app.modules.employee import services
from app.modules.employee.schemas import (
    EmployeeCreate, EmployeeOut, EmployeeDetailOut, 
    EmployeeUpdate, DepartmentCreate, DepartmentOut,
    DepartmentUpdate, DesignationCreate, DesignationOut,
    DesignationUpdate
)

router = APIRouter(prefix="/emp", tags=["Employee Management"])


# ============================================================================
# EMPLOYEE ENDPOINTS
# ============================================================================

@router.post("/employees", status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    request: Request,
    current_user: dict = Depends(require_roles("admin", "hr_manager")),
    db: Session = Depends(get_db)
):
    """Create a new employee - Standard SOP for employee onboarding"""
    request_id = RequestContextManager.get_request_id()
    client_ip, user_agent = RequestContextManager.get_client_info(request)
    
    try:
        # Validate input
        if not payload.employee_code:
            raise ValidationError("Employee code is required", field="employee_code")
        
        # Create employee
        employee = services.create_employee_service(db, payload)
        db.commit()
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user_id=current_user["user_id"],
            user_phone=current_user["phone_number"],
            module="employee",
            action="create",
            resource_type="Employee",
            resource_id=employee.id,
            ip_address=client_ip,
            user_agent=user_agent,
            new_values={
                "employee_code": employee.employee_code,
                "department_id": employee.department_id
            },
            status_str="success"
        )
        
        return ResponseFormatter.created(
            data=employee,
            message="Employee created successfully",
            request_id=request_id
        )
    except HRMSException:
        db.rollback()
        raise
    except services.DuplicateError as e:
        db.rollback()
        raise DuplicateError("Employee", field="employee_code")
    except Exception as e:
        db.rollback()
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to create employee",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/employees/{employee_id}")
def get_employee(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_roles()),
    db: Session = Depends(get_db)
):
    """Get employee details by ID"""
    request_id = RequestContextManager.get_request_id()
    
    try:
        employee = services.get_employee_by_id(db, employee_id)
        if not employee:
            raise ResourceNotFoundError("Employee", employee_id)
        
        return ResponseFormatter.success(
            data=employee,
            message="Employee details retrieved",
            request_id=request_id
        )
    except HRMSException:
        raise
    except Exception as e:
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to fetch employee",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/employees")
def get_all_employees(
    request: Request,
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Number of records to return"),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: dict = Depends(require_roles()),
    db: Session = Depends(get_db)
):
    """List all employees with pagination and filters - Standard SOP"""
    request_id = RequestContextManager.get_request_id()
    
    try:
        result = services.get_all_employees(
            db=db,
            skip=offset,
            limit=limit,
            department_id=department_id,
            is_active=is_active
        )
        
        total = result.get("total", 0)
        employees = result.get("data", [])
        
        return ResponseFormatter.paginated(
            items=employees,
            total=total,
            skip=offset,
            limit=limit,
            message="Employees retrieved successfully",
            request_id=request_id
        )
    except HRMSException:
        raise
    except Exception as e:
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to fetch employees",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.put("/employees/{employee_id}")
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    request: Request,
    current_user: dict = Depends(require_roles("admin", "hr_manager")),
    db: Session = Depends(get_db)
):
    """Update employee information - Standard SOP"""
    request_id = RequestContextManager.get_request_id()
    client_ip, user_agent = RequestContextManager.get_client_info(request)
    
    try:
        # Get existing employee
        existing_employee = services.get_employee_by_id(db, employee_id)
        if not existing_employee:
            raise ResourceNotFoundError("Employee", employee_id)
        
        old_values = {
            "department_id": existing_employee.department_id,
            "is_active": existing_employee.is_active
        }
        
        # Update employee
        employee = services.update_employee(db, employee_id, payload)
        db.commit()
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user_id=current_user["user_id"],
            user_phone=current_user["phone_number"],
            module="employee",
            action="update",
            resource_type="Employee",
            resource_id=employee.id,
            ip_address=client_ip,
            user_agent=user_agent,
            old_values=old_values,
            new_values={
                "department_id": employee.department_id,
                "is_active": employee.is_active
            },
            status_str="success"
        )
        
        return ResponseFormatter.success(
            data=employee,
            message="Employee updated successfully",
            request_id=request_id
        )
    except HRMSException:
        db.rollback()
        raise
    except services.DuplicateError as e:
        db.rollback()
        raise DuplicateError("Employee")
    except Exception as e:
        db.rollback()
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to update employee",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    """Soft delete employee - Standard SOP"""
    client_ip, user_agent = RequestContextManager.get_client_info(request)
    
    try:
        # Verify employee exists
        existing_employee = services.get_employee_by_id(db, employee_id)
        if not existing_employee:
            raise ResourceNotFoundError("Employee", employee_id)
        
        # Delete employee (soft delete)
        services.delete_employee(db, employee_id)
        db.commit()
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user_id=current_user["user_id"],
            user_phone=current_user["phone_number"],
            module="employee",
            action="delete",
            resource_type="Employee",
            resource_id=employee_id,
            ip_address=client_ip,
            user_agent=user_agent,
            status_str="success"
        )
        
        return None
    except HRMSException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to delete employee",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# DEPARTMENT ENDPOINTS
# ============================================================================

@router.post("/departments", status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    request: Request,
    current_user: dict = Depends(require_roles("admin", "hr_manager")),
    db: Session = Depends(get_db)
):
    """Create a new department"""
    request_id = RequestContextManager.get_request_id()
    client_ip, user_agent = RequestContextManager.get_client_info(request)
    
    try:
        if not payload.name or len(payload.name.strip()) == 0:
            raise ValidationError("Department name is required", field="name")
        
        department = services.create_department_service(db, payload)
        db.commit()
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user_id=current_user["user_id"],
            user_phone=current_user["phone_number"],
            module="employee",
            action="create",
            resource_type="Department",
            resource_id=department.id,
            ip_address=client_ip,
            user_agent=user_agent,
            new_values={"name": department.name},
            status_str="success"
        )
        
        return ResponseFormatter.created(
            data=department,
            message="Department created successfully",
            request_id=request_id
        )
    except HRMSException:
        db.rollback()
        raise
    except services.DuplicateError as e:
        db.rollback()
        raise DuplicateError("Department", field="name")
    except Exception as e:
        db.rollback()
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to create department",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/departments")
def list_departments(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: dict = Depends(require_roles()),
    db: Session = Depends(get_db)
):
    """List all departments with pagination"""
    request_id = RequestContextManager.get_request_id()
    
    try:
        result = services.list_departments(db, skip=skip, limit=limit)
        total = result.get("total", 0)
        departments = result.get("data", [])
        
        return ResponseFormatter.paginated(
            items=departments,
            total=total,
            skip=skip,
            limit=limit,
            message="Departments retrieved successfully",
            request_id=request_id
        )
    except HRMSException:
        raise
    except Exception as e:
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to fetch departments",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/departments/{department_id}")
def get_department(
    department_id: int,
    request: Request,
    current_user: dict = Depends(require_roles()),
    db: Session = Depends(get_db)
):
    """Get department by ID"""
    request_id = RequestContextManager.get_request_id()
    
    try:
        department = services.get_department_by_id(db, department_id)
        if not department:
            raise ResourceNotFoundError("Department", department_id)
        
        return ResponseFormatter.success(
            data=department,
            message="Department details retrieved",
            request_id=request_id
        )
    except HRMSException:
        raise
    except Exception as e:
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to fetch department",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.put("/departments/{department_id}")
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    request: Request,
    current_user: dict = Depends(require_roles("admin", "hr_manager")),
    db: Session = Depends(get_db)
):
    """Update department information"""
    request_id = RequestContextManager.get_request_id()
    client_ip, user_agent = RequestContextManager.get_client_info(request)
    
    try:
        existing_department = services.get_department_by_id(db, department_id)
        if not existing_department:
            raise ResourceNotFoundError("Department", department_id)
        
        old_values = {"name": existing_department.name}
        
        department = services.update_department(db, department_id, payload)
        db.commit()
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user_id=current_user["user_id"],
            user_phone=current_user["phone_number"],
            module="employee",
            action="update",
            resource_type="Department",
            resource_id=department.id,
            ip_address=client_ip,
            user_agent=user_agent,
            old_values=old_values,
            new_values={"name": department.name},
            status_str="success"
        )
        
        return ResponseFormatter.success(
            data=department,
            message="Department updated successfully",
            request_id=request_id
        )
    except HRMSException:
        db.rollback()
        raise
    except services.DuplicateError as e:
        db.rollback()
        raise DuplicateError("Department", field="name")
    except Exception as e:
        db.rollback()
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to update department",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: int,
    request: Request,
    current_user: dict = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    """Delete department"""
    client_ip, user_agent = RequestContextManager.get_client_info(request)
    
    try:
        existing_department = services.get_department_by_id(db, department_id)
        if not existing_department:
            raise ResourceNotFoundError("Department", department_id)
        
        services.delete_department(db, department_id)
        db.commit()
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user_id=current_user["user_id"],
            user_phone=current_user["phone_number"],
            module="employee",
            action="delete",
            resource_type="Department",
            resource_id=department_id,
            ip_address=client_ip,
            user_agent=user_agent,
            status_str="success"
        )
        
        return None
    except HRMSException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to delete department",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# DESIGNATION ENDPOINTS
# ============================================================================

@router.post("/designations", status_code=status.HTTP_201_CREATED)
def create_designation(
    payload: DesignationCreate,
    request: Request,
    current_user: dict = Depends(require_roles("admin", "hr_manager")),
    db: Session = Depends(get_db)
):
    """Create a new designation"""
    request_id = RequestContextManager.get_request_id()
    client_ip, user_agent = RequestContextManager.get_client_info(request)
    
    try:
        if not payload.title or len(payload.title.strip()) == 0:
            raise ValidationError("Designation title is required", field="title")
        
        designation = services.create_designation_service(db, payload)
        db.commit()
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user_id=current_user["user_id"],
            user_phone=current_user["phone_number"],
            module="employee",
            action="create",
            resource_type="Designation",
            resource_id=designation.id,
            ip_address=client_ip,
            user_agent=user_agent,
            new_values={"title": designation.title},
            status_str="success"
        )
        
        return ResponseFormatter.created(
            data=designation,
            message="Designation created successfully",
            request_id=request_id
        )
    except HRMSException:
        db.rollback()
        raise
    except services.DuplicateError as e:
        db.rollback()
        raise DuplicateError("Designation", field="title")
    except Exception as e:
        db.rollback()
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to create designation",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/designations")
def list_designations(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: dict = Depends(require_roles()),
    db: Session = Depends(get_db)
):
    """List all designations with pagination"""
    request_id = RequestContextManager.get_request_id()
    
    try:
        result = services.list_designations(db, skip=skip, limit=limit)
        total = result.get("total", 0)
        designations = result.get("data", [])
        
        return ResponseFormatter.paginated(
            items=designations,
            total=total,
            skip=skip,
            limit=limit,
            message="Designations retrieved successfully",
            request_id=request_id
        )
    except HRMSException:
        raise
    except Exception as e:
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to fetch designations",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/designations/{designation_id}")
def get_designation(
    designation_id: int,
    request: Request,
    current_user: dict = Depends(require_roles()),
    db: Session = Depends(get_db)
):
    """Get designation by ID"""
    request_id = RequestContextManager.get_request_id()
    
    try:
        designation = services.get_designation_by_id(db, designation_id)
        if not designation:
            raise ResourceNotFoundError("Designation", designation_id)
        
        return ResponseFormatter.success(
            data=designation,
            message="Designation details retrieved",
            request_id=request_id
        )
    except HRMSException:
        raise
    except Exception as e:
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to fetch designation",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.put("/designations/{designation_id}")
def update_designation(
    designation_id: int,
    payload: DesignationUpdate,
    request: Request,
    current_user: dict = Depends(require_roles("admin", "hr_manager")),
    db: Session = Depends(get_db)
):
    """Update designation information"""
    request_id = RequestContextManager.get_request_id()
    client_ip, user_agent = RequestContextManager.get_client_info(request)
    
    try:
        existing_designation = services.get_designation_by_id(db, designation_id)
        if not existing_designation:
            raise ResourceNotFoundError("Designation", designation_id)
        
        old_values = {"title": existing_designation.title}
        
        designation = services.update_designation(db, designation_id, payload)
        db.commit()
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user_id=current_user["user_id"],
            user_phone=current_user["phone_number"],
            module="employee",
            action="update",
            resource_type="Designation",
            resource_id=designation.id,
            ip_address=client_ip,
            user_agent=user_agent,
            old_values=old_values,
            new_values={"title": designation.title},
            status_str="success"
        )
        
        return ResponseFormatter.success(
            data=designation,
            message="Designation updated successfully",
            request_id=request_id
        )
    except HRMSException:
        db.rollback()
        raise
    except services.DuplicateError as e:
        db.rollback()
        raise DuplicateError("Designation", field="title")
    except Exception as e:
        db.rollback()
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to update designation",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete("/designations/{designation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_designation(
    designation_id: int,
    request: Request,
    current_user: dict = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    """Delete designation"""
    client_ip, user_agent = RequestContextManager.get_client_info(request)
    
    try:
        existing_designation = services.get_designation_by_id(db, designation_id)
        if not existing_designation:
            raise ResourceNotFoundError("Designation", designation_id)
        
        services.delete_designation(db, designation_id)
        db.commit()
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user_id=current_user["user_id"],
            user_phone=current_user["phone_number"],
            module="employee",
            action="delete",
            resource_type="Designation",
            resource_id=designation_id,
            ip_address=client_ip,
            user_agent=user_agent,
            status_str="success"
        )
        
        return None
    except HRMSException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HRMSException(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to delete designation",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Employee endpoints
@router.post("/employees", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db)
):
    """Create a new employee"""
    try:
        employee = services.create_employee_service(db, payload)
        db.commit()
        return employee
    except services.NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.DuplicateError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except services.EmployeeServiceError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/employees/{employee_id}", response_model=EmployeeDetailOut)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db)
):
    """Get employee by ID"""
    try:
        employee = services.get_employee_by_id(db, employee_id)
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        return employee
    except services.EmployeeServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/employees", response_model=List[EmployeeDetailOut])
def get_all_employees(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    department_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all employees with optional filters"""
    try:
        return services.get_all_employees(
            db=db,
            skip=offset, 
            limit=limit, 
            department_id=department_id,
            is_active=is_active
        )
    except services.EmployeeServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int, 
    payload: EmployeeUpdate,
    db: Session = Depends(get_db)
):
    """Update employee information with all available fields"""
    try:
        employee = services.update_employee(db, employee_id, payload)
        db.commit()
        return employee
    except services.NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.DuplicateError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except services.EmployeeServiceError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
    

    
@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db)
):
    """Soft delete employee"""
    try:
        services.delete_employee(db, employee_id)
        db.commit()
        return None
    except services.NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.EmployeeServiceError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# Department endpoints
@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db)
):
    """Create a new department"""
    try:
        department = services.create_department_service(db, payload)
        db.commit()
        return department
    except services.DuplicateError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except services.EmployeeServiceError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/departments", response_model=List[DepartmentOut])
def list_departments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List all departments"""
    try:
        departments = services.list_departments(db, skip=skip, limit=limit)
        
        # Add employee count
        result = []
        for dept in departments:
            dept_dict = {
                "id": dept.id,
                "name": dept.name,
                "description": dept.description,
                "created_at": dept.created_at,
                "updated_at": dept.updated_at,
                "employee_count": dept.employees.count() if hasattr(dept, 'employees') else 0
            }
            result.append(DepartmentOut.model_validate(dept_dict))
        
        return result
    except services.EmployeeServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/departments/{department_id}", response_model=DepartmentOut)
def get_department(
    department_id: int,
    db: Session = Depends(get_db)
):
    """Get department by ID"""
    try:
        department = services.get_department_by_id(db, department_id)
        if not department:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        
        dept_dict = {
            "id": department.id,
            "name": department.name,
            "description": department.description,
            "created_at": department.created_at,
            "updated_at": department.updated_at,
            "employee_count": department.employees.count() if hasattr(department, 'employees') else 0
        }
        return DepartmentOut.model_validate(dept_dict)
    except services.EmployeeServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put("/departments/{department_id}", response_model=DepartmentOut)
def update_department(
    department_id: int, 
    payload: DepartmentUpdate,
    db: Session = Depends(get_db)
):
    """Update department information"""
    try:
        department = services.update_department(db, department_id, payload)
        db.commit()
        
        dept_dict = {
            "id": department.id,
            "name": department.name,
            "description": department.description,
            "created_at": department.created_at,
            "updated_at": department.updated_at,
            "employee_count": department.employees.count() if hasattr(department, 'employees') else 0
        }
        return DepartmentOut.model_validate(dept_dict)
    except services.NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.DuplicateError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except services.EmployeeServiceError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db)
):
    """Delete department"""
    try:
        services.delete_department(db, department_id)
        db.commit()
        return None
    except services.NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.EmployeeServiceError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# Designation endpoints
@router.post("/designations", response_model=DesignationOut, status_code=status.HTTP_201_CREATED)
def create_designation(
    payload: DesignationCreate,
    db: Session = Depends(get_db)
):
    """Create a new designation"""
    try:
        designation = services.create_designation_service(db, payload)
        db.commit()
        return designation
    except services.DuplicateError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except services.EmployeeServiceError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/designations", response_model=List[DesignationOut])
def list_designations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List all designations"""
    try:
        designations = services.list_designations(db, skip=skip, limit=limit)
        
        # Add employee count
        result = []
        for des in designations:
            des_dict = {
                "id": des.id,
                "title": des.title,
                "description": des.description,
                "created_at": des.created_at,
                "updated_at": des.updated_at,
                "employee_count": des.employees.count() if hasattr(des, 'employees') else 0
            }
            result.append(DesignationOut.model_validate(des_dict))
        
        return result
    except services.EmployeeServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/designations/{designation_id}", response_model=DesignationOut)
def get_designation(
    designation_id: int,
    db: Session = Depends(get_db)
):
    """Get designation by ID"""
    try:
        designation = services.get_designation_by_id(db, designation_id)
        if not designation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Designation not found")
        
        des_dict = {
            "id": designation.id,
            "title": designation.title,
            "description": designation.description,
            "created_at": designation.created_at,
            "updated_at": designation.updated_at,
            "employee_count": designation.employees.count() if hasattr(designation, 'employees') else 0
        }
        return DesignationOut.model_validate(des_dict)
    except services.EmployeeServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put("/designations/{designation_id}", response_model=DesignationOut)
def update_designation(
    designation_id: int, 
    payload: DesignationUpdate,
    db: Session = Depends(get_db)
):
    """Update designation information"""
    try:
        designation = services.update_designation(db, designation_id, payload)
        db.commit()
        
        des_dict = {
            "id": designation.id,
            "title": designation.title,
            "description": designation.description,
            "created_at": designation.created_at,
            "updated_at": designation.updated_at,
            "employee_count": designation.employees.count() if hasattr(designation, 'employees') else 0
        }
        return DesignationOut.model_validate(des_dict)
    except services.NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.DuplicateError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except services.EmployeeServiceError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/designations/{designation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_designation(
    designation_id: int,
    db: Session = Depends(get_db)
):
    """Delete designation"""
    try:
        services.delete_designation(db, designation_id)
        db.commit()
        return None
    except services.NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.EmployeeServiceError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")