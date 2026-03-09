import sys

sys.path.insert(0, "src")

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from office_hero.models import Base, User

# Create synchronous engine for user creation
engine = create_engine("postgresql://postgres:pass@localhost:5432/test", echo=True)

# Create tables
Base.metadata.create_all(engine)
print("✓ Database tables created")

# Create test user
with Session(engine) as session:
    # Check if user exists
    existing = session.query(User).filter_by(email="test@example.com").first()
    if existing:
        print(f"✓ Test user already exists: {existing.email}")
    else:
        # Create new user
        user = User(
            email="test@example.com",
            password_hash="$2b$12$...",  # Placeholder
        )
        session.add(user)
        session.commit()
        print(f"✓ Test user created: {user.email}")
