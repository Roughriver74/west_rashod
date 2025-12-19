"""Script to create admin user and initial department."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.db.models import User, Department, UserRoleEnum
from app.utils.auth import get_password_hash


def create_admin():
    """Create admin user and default department if not exist."""
    db = SessionLocal()
    try:
        # Check if department exists
        dept = db.query(Department).filter(Department.code == "DEFAULT").first()
        if not dept:
            dept = Department(
                name="Default Department",
                code="DEFAULT",
                description="Default department for initial setup",
                is_active=True
            )
            db.add(dept)
            db.commit()
            db.refresh(dept)
            print(f"Created department: {dept.name} (ID: {dept.id})")
        else:
            print(f"Department already exists: {dept.name} (ID: {dept.id})")

        # Check if admin user exists
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@westrashod.local",
                full_name="Administrator",
                hashed_password=get_password_hash("admin"),
                role=UserRoleEnum.ADMIN,
                department_id=dept.id,
                is_active=True,
                is_verified=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"Created admin user: {admin.username} (password: admin)")
        else:
            print(f"Admin user already exists: {admin.username}")

        print("\nSetup complete!")
        print("Login URL: http://localhost:8001/docs")
        print("Username: admin")
        print("Password: admin")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
