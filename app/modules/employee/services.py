from typing import Optional, Dict, Any, List
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.modules.admin.models import User
from app.modules.employee.models import Employee, Department, Designation
from app.modules.employee.schemas import (
    EmployeeCreate, EmployeeUpdate, 
    DepartmentCreate, DesignationCreate
)

import logging

logger = logging.getLogger(__name__)


class EmployeeServiceError(Exception):
    """Base exception for employee service"""
    pass


class NotFoundError(EmployeeServiceError):
    """Resource not found"""
    pass


class DuplicateError(EmployeeServiceError):
    """Duplicate resource"""
    pass


def _resolve_fk(val, model, db: Session) -> Optional[int]:
    """
    Resolve a foreign key field which may be an integer id or a name/title string.
    Returns the integer id if found, otherwise None.
    """
    if val is None:
        return None
    
    # If it's already an integer, return it
    if isinstance(val, int):
        return val
    
    # Try to convert to int if it's a string containing only digits
    if isinstance(val, str) and val.isdigit():
        return int(val)
    
    # Look up by text attribute
    try:
        if hasattr(model, "name"):
            obj = db.execute(select(model).where(model.name == val)).scalar_one_or_none()
        elif hasattr(model, "title"):
            obj = db.execute(select(model).where(model.title == val)).scalar_one_or_none()
        else:
            return None
        
        return obj.id if obj else None
    except Exception as e:
        logger.error(f"Error resolving FK for {model.__name__}: {e}")
        return None


def _generate_employee_code(user_id: int) -> str:
    """Generate a unique employee code"""
    return f"EMP{user_id:06d}"


def _enrich_employee_with_names(employee: Employee, db: Session) -> Dict:
    """Add department and designation names to employee dict"""
    employee_dict = {
        "id": employee.id,
        "user_id": employee.user_id,
        "employee_code": employee.employee_code,
        "department_id": employee.department_id,
        "designation_id": employee.designation_id,
        "created_at": employee.created_at,
        "updated_at": employee.updated_at,
        "date_of_joining": employee.date_of_joining,
        "date_of_leaving": employee.date_of_leaving,
        "is_active": employee.is_active,
        "manager_id": employee.manager_id,
        "street1": employee.street1,
        "street2": employee.street2,
        "city": employee.city,
        "state": employee.state,
        "country": employee.country,
        "zip_code": employee.zip_code,
        "permanent_street1": employee.permanent_street1,
        "permanent_street2": employee.permanent_street2,
        "permanent_city": employee.permanent_city,
        "permanent_state": employee.permanent_state,
        "permanent_country": employee.permanent_country,
        "permanent_zip_code": employee.permanent_zip_code,
        "date_of_birth": employee.date_of_birth,
        "gender": employee.gender,
        "blood_group": employee.blood_group,
        "emergency_contact": employee.emergency_contact,
        "uan_number": employee.uan_number,
        "pan_number": employee.pan_number,
        "aadhar_number": employee.aadhar_number,
        "passport_number": employee.passport_number,
        "esic_number": employee.esic_number,    
        "bank_account_number": employee.bank_account_number,
        "pf_number": employee.pf_number,
        "bank_name": employee.bank_name,
        "bank_ifsc_code": employee.bank_ifsc_code,
        "bank_branch": employee.bank_branch
    }
    
    # Add user details
    if employee.user:
        employee_dict.update({
            "first_name": employee.user.first_name,
            "last_name": employee.user.last_name,
            "email": employee.user.email,
            "phone_number": employee.user.phone_number,
        })
    
    # Add department name
    if employee.department_id and employee.department:
        employee_dict["department_name"] = employee.department.name
    
    # Add designation title
    if employee.designation_id and employee.designation:
        employee_dict["designation_title"] = employee.designation.title
    
    return employee_dict


# Employee Services
def create_employee_service(db: Session, employee_data: EmployeeCreate) -> Employee:
    """Create a new employee with associated user"""
    try:
        # Check if user already exists
        existing_user = db.execute(
            select(User).where(
                (User.email == employee_data.email) |
                (User.phone_number == employee_data.phone_number)
            )
        ).scalar_one_or_none()
        
        if existing_user:
            # Check if this user already has an employee record
            existing_employee = db.execute(
                select(Employee).where(Employee.user_id == existing_user.id)
            ).scalar_one_or_none()
            
            if existing_employee:
                raise DuplicateError("Employee record already exists for this user")
            
            user_id = existing_user.id
        else:
            # Create new user (password will be set by auth module separately)
            user = User(
                first_name=employee_data.first_name,
                last_name=employee_data.last_name,
                email=employee_data.email,
                phone_number=employee_data.phone_number
            )
            db.add(user)
            db.flush()  # Get user.id without committing
            user_id = user.id
        
        # Resolve department and designation
        dep_id = _resolve_fk(employee_data.department, Department, db)
        desig_id = _resolve_fk(employee_data.designation, Designation, db)
        
        # Create employee
        new_employee = Employee(
            user_id=user_id,
            employee_code=user_id.employee_code,
            department_id=dep_id,
            designation_id=desig_id,
        )
        db.add(new_employee)
        db.flush()
        
        # Refresh to load relationships
        db.refresh(new_employee, ['user', 'department', 'designation'])
        
        return new_employee
        
    except IntegrityError as e:
        logger.error(f"Integrity error creating employee: {e}")
        db.rollback()
        raise DuplicateError("Employee with this data already exists")
    except Exception as e:
        logger.error(f"Error creating employee: {e}")
        db.rollback()
        raise EmployeeServiceError(f"Failed to create employee: {str(e)}")


def get_employee_by_id(db: Session, employee_id: int) -> Optional[Employee]:
    """Get employee by ID"""
    return db.execute(
        select(Employee)
        .options(joinedload(Employee.user), joinedload(Employee.department), joinedload(Employee.designation))
        .where(Employee.id == employee_id)
    ).scalar_one_or_none()


def get_all_employees(
    db: Session,
    skip: int = 0, 
    limit: int = 100, 
    department_id: Optional[int] = None,
    is_active: Optional[bool] = None
) -> List[Employee]:
    """Get all employees with pagination and filters"""
    query = select(Employee).options(
        joinedload(Employee.user), 
        joinedload(Employee.department), 
        joinedload(Employee.designation)
    )
    
    if department_id is not None:
        query = query.where(Employee.department_id == department_id)
    
    if is_active is not None:
        query = query.where(Employee.is_active == is_active)
    
    query = query.offset(skip).limit(limit)
    return db.execute(query).scalars().all()


def update_employee(db: Session, employee_id: int, updates: EmployeeUpdate) -> Employee:
    """Update employee information with all available fields"""
    employee = db.execute(
        select(Employee)
        .options(joinedload(Employee.user))
        .where(Employee.id == employee_id)
    ).scalar_one_or_none()
    
    if not employee:
        raise NotFoundError("Employee not found")
    
    # Update department/designation
    if updates.department is not None:
        employee.department_id = _resolve_fk(updates.department, Department, db)
    
    if updates.designation is not None:
        employee.designation_id = _resolve_fk(updates.designation, Designation, db)
    
    # Update employee fields
    employee_fields = [
        'date_of_joining', 'date_of_leaving', 'is_active', 'manager_id',
        'street1', 'street2', 'city', 'state', 'country', 'zip_code',
        'permanent_street1', 'permanent_street2', 'permanent_city', 
        'permanent_state', 'permanent_country', 'permanent_zip_code',
        'date_of_birth', 'gender', 'blood_group', 'emergency_contact',
        'uan_number', 'pan_number', 'aadhar_number', 'passport_number',
        'esic_number', 'pf_number', 'bank_account_number', 'bank_name',
        'bank_ifsc_code', 'bank_branch'
    ]
    
    for field in employee_fields:
        if hasattr(updates, field) and getattr(updates, field) is not None:
            setattr(employee, field, getattr(updates, field))
    
    # Update user fields if user exists
    if employee.user:
        user_fields = ['first_name', 'last_name', 'email', 'phone_number']
        for field in user_fields:
            if hasattr(updates, field) and getattr(updates, field) is not None:
                # Special handling for email uniqueness
                if field == 'email':
                    existing_user = db.execute(
                        select(User).where(
                            User.email == getattr(updates, field),
                            User.id != employee.user_id
                        )
                    ).scalar_one_or_none()
                    if existing_user:
                        raise DuplicateError("Email already in use")
                
                setattr(employee.user, field, getattr(updates, field))
    
    db.flush()
    db.refresh(employee, ['user', 'department', 'designation'])
    return employee

def delete_employee(db: Session, employee_id: int) -> None:
    """Soft delete employee"""
    employee = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    
    if not employee:
        raise NotFoundError("Employee not found")
    
    employee.is_active = False
    db.flush()


# Department Services
def create_department_service(db: Session, department_data: DepartmentCreate) -> Department:
    """Create a new department"""
    try:
        # Check for existing department
        existing = db.execute(
            select(Department).where(Department.name == department_data.name)
        ).scalar_one_or_none()
        
        if existing:
            raise DuplicateError("Department with this name already exists")
        
        new_department = Department(
            name=department_data.name,
            description=department_data.description
        )
        db.add(new_department)
        db.flush()
        db.refresh(new_department)
        
        return new_department
        
    except IntegrityError as e:
        logger.error(f"Integrity error creating department: {e}")
        db.rollback()
        raise DuplicateError("Department with this name already exists")


def list_departments(db: Session, skip: int = 0, limit: int = 100) -> List[Department]:
    """List all departments with pagination"""
    return db.execute(
        select(Department).offset(skip).limit(limit)
    ).scalars().all()


def get_department_by_id(db: Session, department_id: int) -> Optional[Department]:
    """Get department by ID"""
    return db.get(Department, department_id)


def update_department(db: Session, department_id: int, updates) -> Department:
    """Update department information"""
    department = db.get(Department, department_id)
    
    if not department:
        raise NotFoundError("Department not found")
    
    if updates.name is not None:
        # Check if new name is unique
        existing = db.execute(
            select(Department).where(
                Department.name == updates.name,
                Department.id != department_id
            )
        ).scalar_one_or_none()
        
        if existing:
            raise DuplicateError("Department with this name already exists")
        
        department.name = updates.name
    
    if updates.description is not None:
        department.description = updates.description
    
    db.flush()
    db.refresh(department)
    return department


def delete_department(db: Session, department_id: int) -> None:
    """Delete department"""
    department = db.get(Department, department_id)
    
    if not department:
        raise NotFoundError("Department not found")
    
    # Check if department has employees
    employee_count = db.execute(
        select(func.count()).select_from(Employee).where(Employee.department_id == department_id)
    ).scalar()
    
    if employee_count > 0:
        raise EmployeeServiceError("Cannot delete department with associated employees")
    
    db.delete(department)
    db.flush()


# Designation Services
def create_designation_service(db: Session, designation_data: DesignationCreate) -> Designation:
    """Create a new designation"""
    try:
        existing = db.execute(
            select(Designation).where(Designation.title == designation_data.title)
        ).scalar_one_or_none()
        
        if existing:
            raise DuplicateError("Designation with this title already exists")
        
        new_designation = Designation(
            title=designation_data.title,
            description=designation_data.description
        )
        db.add(new_designation)
        db.flush()
        db.refresh(new_designation)
        
        return new_designation
        
    except IntegrityError as e:
        logger.error(f"Integrity error creating designation: {e}")
        db.rollback()
        raise DuplicateError("Designation with this title already exists")


def list_designations(db: Session, skip: int = 0, limit: int = 100) -> List[Designation]:
    """List all designations with pagination"""
    return db.execute(
        select(Designation).offset(skip).limit(limit)
    ).scalars().all()


def get_designation_by_id(db: Session, designation_id: int) -> Optional[Designation]:
    """Get designation by ID"""
    return db.get(Designation, designation_id)


def update_designation(db: Session, designation_id: int, updates) -> Designation:
    """Update designation information"""
    designation = db.get(Designation, designation_id)
    
    if not designation:
        raise NotFoundError("Designation not found")
    
    if updates.title is not None:
        # Check if new title is unique
        existing = db.execute(
            select(Designation).where(
                Designation.title == updates.title,
                Designation.id != designation_id
            )
        ).scalar_one_or_none()
        
        if existing:
            raise DuplicateError("Designation with this title already exists")
        
        designation.title = updates.title
    
    if updates.description is not None:
        designation.description = updates.description
    
    db.flush()
    db.refresh(designation)
    return designation


def delete_designation(db: Session, designation_id: int) -> None:
    """Delete designation"""
    designation = db.get(Designation, designation_id)
    
    if not designation:
        raise NotFoundError("Designation not found")
    
    # Check if designation has employees
    employee_count = db.execute(
        select(func.count()).select_from(Employee).where(Employee.designation_id == designation_id)
    ).scalar()
    
    if employee_count > 0:
        raise EmployeeServiceError("Cannot delete designation with associated employees")
    
    db.delete(designation)
    db.flush()