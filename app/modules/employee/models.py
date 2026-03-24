from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.orm import relationship, validates, backref
from datetime import datetime

from app.core.database import Base
from app.modules.admin.models import User


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    employees = relationship("Employee", back_populates="department", lazy="dynamic")


class Designation(Base):
    __tablename__ = "designations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(128), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    employees = relationship("Employee", back_populates="designation", lazy="dynamic")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    designation_id = Column(Integer, ForeignKey("designations.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    employee_code = Column(String(50), unique=True, nullable=False, index=True)
    date_of_joining = Column(DateTime, nullable=True)
    date_of_leaving = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)       
    manager_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Address fields (current)
    street1 = Column(String(256), nullable=True)
    street2 = Column(String(256), nullable=True)
    city = Column(String(128), nullable=True)
    state = Column(String(128), nullable=True)
    country = Column(String(128), nullable=True)
    zip_code = Column(String(20), nullable=True)
    
    # Permanent address
    permanent_street1 = Column(String(256), nullable=True)
    permanent_street2 = Column(String(256), nullable=True)
    permanent_city = Column(String(128), nullable=True)
    permanent_state = Column(String(128), nullable=True)
    permanent_country = Column(String(128), nullable=True)  
    permanent_zip_code = Column(String(20), nullable=True)
    
    # Personal details
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String(20), nullable=True)
    blood_group = Column(String(10), nullable=True)
    emergency_contact = Column(String(20), nullable=True)
    
    # Identification numbers
    uan_number = Column(String(50), unique=True, nullable=True, index=True)
    pan_number = Column(String(50), unique=True, nullable=True, index=True)
    aadhar_number = Column(String(50), unique=True, nullable=True, index=True)
    passport_number = Column(String(50), unique=True, nullable=True, index=True)
    esic_number = Column(String(50), unique=True, nullable=True, index=True)
    pf_number = Column(String(50), unique=True, nullable=True, index=True)
    
    # Bank details
    bank_account_number = Column(String(50), unique=True, nullable=True, index=True)
    bank_name = Column(String(128), nullable=True)
    bank_ifsc_code = Column(String(20), nullable=True)
    bank_branch = Column(String(128), nullable=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Relationships
    user = relationship("User", backref=backref("employee", uselist=False), lazy="joined")
    department = relationship("Department", back_populates="employees", lazy="select")
    designation = relationship("Designation", back_populates="employees", lazy="select")
    manager = relationship("Employee", remote_side=[id], backref="subordinates")

    __table_args__ = (
        CheckConstraint('date_of_leaving IS NULL OR date_of_leaving > date_of_joining', 
                       name='check_leaving_after_joining'),
    )

    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}" if self.user else None