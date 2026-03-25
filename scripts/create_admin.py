#!/usr/bin/env python
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.modules.admin.models import User
from app.modules.employee.models import Employee, Department, Designation


def create_admin():
    session = SessionLocal()
    
    try:
        # Check if admin exists
        existing = session.query(User).filter(User.employee_code == 'admin').first()
        if existing:
            print("✓ Admin user already exists")
            print(f"  Email: {existing.email}")
            print(f"  Employee Code: {existing.employee_code}")
            print(f"  Phone: {existing.phone_number}")
            return
        
        # Create admin user (phone-based authentication)
        admin = User(
            email='admin@example.com',
            employee_code='admin',
            phone_number='10000000000',
            first_name='Admin',
            last_name='User',
            role='admin',
            status='active',
            is_phone_verified=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            roles=['admin']
        )
        session.add(admin)
        session.commit()
        
        print("✓ Admin user created!")
        print(f"  Email: admin@example.com")
        print(f"  Username: admin")
        print(f"  Phone: 10000000000")
        print("\nUse OTP login flow to authenticate as this user.")
        
    finally:
        session.close()

def create_defualt_departments_and_designations():
    session = SessionLocal()
    
    try:
        # Check if departments exist
        if session.query(Department).count() > 0:
            print("✓ Departments already exist")
        else:
            departments = [
                Department(name='HR', description='Human Resources', created_at=datetime.now(),
            updated_at=datetime.now()),
                Department(name='IT', description='Information Technology', created_at=datetime.now(),
            updated_at=datetime.now()),
                Department(name='Marketing', description='Marketing Department', created_at=datetime.now(),
            updated_at=datetime.now()),
                Department(name='Finance', description='Finance Department', created_at=datetime.now(),
            updated_at=datetime.now()),
                Department(name='Operations', description='Operations Department', created_at=datetime.now(),
            updated_at=datetime.now()),
                Department(name='Admin', description='Administration Department', created_at=datetime.now(),
            updated_at=datetime.now()),
                Department(name='Development', description='Software Development Department', created_at=datetime.now(),
            updated_at=datetime.now()),
                Department(name='QA', description='Quality Assurance Department', created_at=datetime.now(),
            updated_at=datetime.now())

            ]
            session.add_all(departments)
            session.commit()
            print("✓ Default departments created")
        if session.query(Designation).count() > 0:
            print("✓ Designations already exist")
        else:
            designations = [
                Designation(title='Manager', description='Manages a team or department', created_at=datetime.now(),
            updated_at=datetime.now()),
                Designation(title='Developer', description='Software Developer', created_at=datetime.now(),
            updated_at=datetime.now()),
                Designation(title='Designer', description='UI/UX Designer', created_at=datetime.now(),
            updated_at=datetime.now()),
                Designation(title='Analyst', description='Business Analyst', created_at=datetime.now(),
            updated_at=datetime.now()),
                Designation(title='Tester', description='Quality Assurance Tester', created_at=datetime.now(),
            updated_at=datetime.now()),
                Designation(title='HR Specialist', description='Human Resources Specialist', created_at=datetime.now(),
            updated_at=datetime.now()),
                Designation(title='IT Support', description='IT Support Specialist', created_at=datetime.now(),
            updated_at=datetime.now()),
                Designation(title='Marketing Specialist', description='Marketing Specialist', created_at=datetime.now(),
            updated_at=datetime.now())
            ]
            session.add_all(designations)
            session.commit()
            print("✓ Default designations created")
    except Exception as e:
        print(f"Error creating designations: {e}")
    finally:
        session.close()

def create_defult_employee()

if __name__ == '__main__':
    create_admin()
    create_defualt_departments_and_designations()
