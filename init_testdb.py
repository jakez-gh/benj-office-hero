import sys

sys.path.insert(0, "src")

import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Import models
from office_hero.models import Base, User

# Sync engine
engine = create_engine("postgresql://postgres:pass@localhost:5432/test", echo=False)

# Create all tables
Base.metadata.create_all(engine)
print("✓ Database schema created")

# Create test user
with Session(engine) as session:
    existing = session.query(User).filter_by(email="test@example.com").first()
    if existing:
        print("✓ User already exists: test@example.com")
    else:
        # Hash password
        password_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode("utf-8")

        user = User(
            email="test@example.com", password_hash=password_hash, role="admin", active=True
        )
        session.add(user)
        session.commit()
        print("✓ Test user created: test@example.com / password123")

print("✓ Database ready for testing")
