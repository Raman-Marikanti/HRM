from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.orm import relationship, backref
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


class BankDetail(Base):
    __tablename__ = "bank_details"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    bank_account_number = Column(String(50), unique=True, nullable=False, index=True)
    bank_name = Column(String(128), nullable=False)
    bank_ifsc_code = Column(String(20), nullable=False)
    bank_branch = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="bank_detail")


class EmployeeDocumentDetail(Base):
    __tablename__ = "employee_document_details"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    pancard_number = Column(String(50), unique=True, nullable=True, index=True)
    aadhar_number = Column(String(50), unique=True, nullable=True, index=True)
    passport_number = Column(String(50), unique=True, nullable=True, index=True)
    esic_number = Column(String(50), unique=True, nullable=True, index=True)
    uan_number = Column(String(50), unique=True, nullable=True, index=True)
    pf_number = Column(String(50), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = relationship("Employee", back_populates="employee_document_detail")


class EmployeePersonalDetail(Base):
    __tablename__ = "employee_personal_details"

    id = Column(Integer, primary_key=True, index=True)
    employee_profile_picture = Column(String(256), nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String(20), nullable=True)
    blood_group = Column(String(10), nullable=True)
    emergency_contact = Column(String(20), nullable=True)

    address_street1 = Column(String(256), nullable=True)
    address_street2 = Column(String(256), nullable=True)
    address_city = Column(String(128), nullable=True)
    address_state = Column(String(128), nullable=True)
    address_country = Column(String(128), nullable=True)
    address_zip_code = Column(String(20), nullable=True)

    perminent_address_street1 = Column(String(256), nullable=True)
    perminent_address_street2 = Column(String(256), nullable=True)
    perminent_address_city = Column(String(128), nullable=True)
    perminent_address_state = Column(String(128), nullable=True)
    perminent_address_country = Column(String(128), nullable=True)
    perminent_address_zip_code = Column(String(20), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = relationship("Employee", back_populates="employee_personal_detail")


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    qualification = Column(String(256), nullable=True)
    experience = Column(String(256), nullable=True)
    skills = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = relationship("Employee", back_populates="employee_profile")


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

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Relationships
    user = relationship("User", backref=backref("employee", uselist=False), lazy="joined")
    department = relationship("Department", back_populates="employees", lazy="select")
    designation = relationship("Designation", back_populates="employees", lazy="select")
    manager = relationship("Employee", remote_side=[id], backref="subordinates")

    employee_personal_detail = relationship(
        "EmployeePersonalDetail",
        back_populates="employee",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined"
    )

    employee_document_detail = relationship(
        "EmployeeDocumentDetail",
        back_populates="employee",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined"
    )

    bank_detail = relationship(
        "BankDetail",
        back_populates="employee",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined"
    )

    employee_profile = relationship(
        "EmployeeProfile",
        back_populates="employee",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined"
    )

    # __table_args__ = (
    #     CheckConstraint(
    #         "date_of_leaving IS NOT NULL OR date_of_leaving > date_of_joining",
    #         name="check_leaving_after_joining",
    #     ),
    # )

    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}" if self.user else None