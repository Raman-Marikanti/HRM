# app/modules/employee/schemas.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator

from app.modules.admin.schemas import UserOut

# Department Schemas
class DepartmentBase(BaseModel):
    name: str = Field(..., max_length=128)
    description: Optional[str] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = None

class DepartmentResponse(DepartmentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Designation Schemas
class DesignationBase(BaseModel):
    title: str = Field(..., max_length=128)
    description: Optional[str] = None

class DesignationCreate(DesignationBase):
    pass

class DesignationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = None

class DesignationResponse(DesignationBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Bank Detail Schemas
class BankDetailBase(BaseModel):
    bank_account_number: str = Field(..., max_length=50)
    bank_name: str = Field(..., max_length=128)
    bank_ifsc_code: str = Field(..., max_length=20)
    bank_branch: str = Field(..., max_length=128)

class BankDetailCreate(BankDetailBase):
    pass

class BankDetailUpdate(BankDetailBase):
    bank_account_number: Optional[str] = Field(None, max_length=50)
    bank_name: Optional[str] = Field(None, max_length=128)
    bank_ifsc_code: Optional[str] = Field(None, max_length=20)
    bank_branch: Optional[str] = Field(None, max_length=128)

class BankDetailResponse(BankDetailBase):
    id: int
    employee_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Employee Document Detail Schemas
class EmployeeDocumentDetailBase(BaseModel):
    pancard_number: Optional[str] = Field(None, max_length=50)
    aadhar_number: Optional[str] = Field(None, max_length=50)
    passport_number: Optional[str] = Field(None, max_length=50)
    esic_number: Optional[str] = Field(None, max_length=50)
    uan_number: Optional[str] = Field(None, max_length=50)
    pf_number: Optional[str] = Field(None, max_length=50)

class EmployeeDocumentDetailCreate(EmployeeDocumentDetailBase):
    pass

class EmployeeDocumentDetailUpdate(EmployeeDocumentDetailBase):
    pass

class EmployeeDocumentDetailResponse(EmployeeDocumentDetailBase):
    id: int
    employee_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Employee Personal Detail Schemas
class EmployeePersonalDetailBase(BaseModel):
    employee_profile_picture: Optional[str] = Field(None, max_length=256)
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = Field(None, max_length=20)
    blood_group: Optional[str] = Field(None, max_length=10)
    emergency_contact: Optional[str] = Field(None, max_length=20)
    address_street1: Optional[str] = Field(None, max_length=256)
    address_street2: Optional[str] = Field(None, max_length=256)
    address_city: Optional[str] = Field(None, max_length=128)
    address_state: Optional[str] = Field(None, max_length=128)
    address_country: Optional[str] = Field(None, max_length=128)
    address_zip_code: Optional[str] = Field(None, max_length=20)
    perminent_address_street1: Optional[str] = Field(None, max_length=256)
    perminent_address_street2: Optional[str] = Field(None, max_length=256)
    perminent_address_city: Optional[str] = Field(None, max_length=128)
    perminent_address_state: Optional[str] = Field(None, max_length=128)
    perminent_address_country: Optional[str] = Field(None, max_length=128)
    perminent_address_zip_code: Optional[str] = Field(None, max_length=20)

class EmployeePersonalDetailCreate(EmployeePersonalDetailBase):
    pass

class EmployeePersonalDetailUpdate(EmployeePersonalDetailBase):
    pass

class EmployeePersonalDetailResponse(EmployeePersonalDetailBase):
    id: int
    employee_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Employee Profile Schemas
class EmployeeProfileBase(BaseModel):
    qualification: Optional[str] = Field(None, max_length=256)
    experience: Optional[str] = Field(None, max_length=256)
    skills: Optional[str] = Field(None, max_length=512)

class EmployeeProfileCreate(EmployeeProfileBase):
    pass

class EmployeeProfileUpdate(EmployeeProfileBase):
    pass

class EmployeeProfileResponse(EmployeeProfileBase):
    id: int
    employee_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Employee Schemas
class EmployeeBase(BaseModel):
    date_of_joining: Optional[datetime] = None
    date_of_leaving: Optional[datetime] = None
    is_active: bool = True
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    manager_id: Optional[int] = None


class EmployeeCreate(EmployeeBase):
    user_id: int
    employee_code: str
    bank_detail: Optional[BankDetailCreate] = None
    employee_personal_detail: Optional[EmployeePersonalDetailCreate] = None
    employee_document_detail: Optional[EmployeeDocumentDetailCreate] = None
    employee_profile: Optional[EmployeeProfileCreate] = None

class EmployeeUpdate(BaseModel):
    date_of_joining: Optional[datetime] = None
    date_of_leaving: Optional[datetime] = None
    is_active: Optional[bool] = None
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    manager_id: Optional[int] = None
    bank_detail: Optional[BankDetailUpdate] = None
    employee_personal_detail: Optional[EmployeePersonalDetailUpdate] = None
    employee_document_detail: Optional[EmployeeDocumentDetailUpdate] = None
    employee_profile: Optional[EmployeeProfileUpdate] = None

class ManagerResponse(BaseModel):
    id: int
    full_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class EmployeeResponse(EmployeeBase):
    id: int 
    user_id: int
    created_at: datetime
    updated_at: datetime
    full_name: Optional[str] = None
    
    # Related data
    user: Optional[UserOut] = None
    department: Optional[DepartmentResponse] = None
    designation: Optional[DesignationResponse] = None
    manager: Optional[ManagerResponse] = None
    bank_detail: Optional[BankDetailResponse] = None
    employee_personal_detail: Optional[EmployeePersonalDetailResponse] = None
    employee_document_detail: Optional[EmployeeDocumentDetailResponse] = None
    employee_profile: Optional[EmployeeProfileResponse] = None
    
    class Config:
        from_attributes = True

# For circular reference
EmployeeResponse.model_rebuild()

# Employee List Response
class EmployeeListResponse(BaseModel):
    id: int
    employee_code: str
    full_name: Optional[str] = None
    department: Optional[DepartmentResponse] = None
    designation: Optional[DesignationResponse] = None
    is_active: bool
    date_of_joining: Optional[datetime] = None
    
    class Config:
        from_attributes = True