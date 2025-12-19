"""Script to create admin user."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.db.models import User, UserRoleEnum
from app.utils.auth import get_password_hash


def create_admin():
    """Create admin user if not exists."""
    db = SessionLocal()
    try:
        # Check if admin user exists
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@westrashod.dev",
                full_name="Administrator",
                hashed_password=get_password_hash("admin"),
                role=UserRoleEnum.ADMIN,
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
        print("Login URL: http://localhost:8005/docs")
        print("Username: admin")
        print("Password: admin")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
