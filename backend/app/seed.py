"""
Seed script — run once after migrations:
  docker compose exec backend python -m app.seed
"""
import asyncio
import uuid

from passlib.context import CryptContext
from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models import Department, DepartmentType, User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


DEPARTMENTS = [
    DepartmentType.ACADEMY,
    DepartmentType.YOUTH,
    DepartmentType.FIRST_TEAM,
    DepartmentType.MERCHANDISE,
]

SEED_USERS = [
    {
        "name": "Club COO",
        "email": "coo@club.local",
        "password": "changeme123",
        "role": UserRole.COO,
    },
    {
        "name": "Equipment Manager",
        "email": "equipment@club.local",
        "password": "changeme123",
        "role": UserRole.EQUIPMENT_MANAGER,
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        # departments
        for dept_type in DEPARTMENTS:
            existing = await session.scalar(
                select(Department).where(Department.name == dept_type)
            )
            if not existing:
                session.add(Department(id=uuid.uuid4(), name=dept_type))
                print(f"  + Department: {dept_type}")
            else:
                print(f"  ~ Department already exists: {dept_type}")

        # users
        for u in SEED_USERS:
            existing = await session.scalar(
                select(User).where(User.email == u["email"])
            )
            if not existing:
                session.add(
                    User(
                        id=uuid.uuid4(),
                        name=u["name"],
                        email=u["email"],
                        hashed_password=pwd_context.hash(u["password"]),
                        role=u["role"],
                    )
                )
                print(f"  + User: {u['email']} [{u['role']}]")
            else:
                print(f"  ~ User already exists: {u['email']}")

        await session.commit()
        print("\nSeed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
