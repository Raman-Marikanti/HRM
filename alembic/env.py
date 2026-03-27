from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os, sys

# make sure the app package is importable
sys.path.insert(0, os.path.abspath(os.getcwd()))

from app.core.database import Base            # your declarative base
# import modules so their models are registered with Base.metadata
from app.modules.admin import models as auth_models  # noqa: F401
from app.modules.employee import models as emp_models  # noqa: F401

config = context.config
fileConfig(config.config_file_name)
from app.modules.admin.models import User  # noqa: F401
from app.modules.employee.models import Department, Designation, Employee, BankDetail, EmployeeDocumentDetail
from app.modules.attendance.models import Attendance, AttendanceSetting
# this is the metadata object the 'autogenerate' support uses
target_metadata = [
                    User.__table__.metadata,
                    Department.__table__.metadata, 
                    Designation.__table__.metadata, 
                    Employee.__table__.metadata,
                    BankDetail.__table__.metadata,
                    EmployeeDocumentDetail.__table__.metadata,
                    Attendance.__table__.metadata,
                    AttendanceSetting.__table__.metadata
                    ]

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
