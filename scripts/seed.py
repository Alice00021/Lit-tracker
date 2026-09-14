"""
Seed-скрипт для создания тестовых данных.
Запуск: python -m scripts.seed
"""
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import User


TEST_USERS = [
    {
        "email": "alice@example.com",
        "hashed_password": "not-a-real-hash-just-for-test",
    },
    {
        "email": "bob@example.com",
        "hashed_password": "not-a-real-hash-just-for-test",
    },
]


async def seed_users() -> None:
    async with AsyncSessionLocal() as session:
        for user_data in TEST_USERS:
            stmt = select(User).where(User.email == user_data["email"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"⏭️  User {user_data['email']} already exists (id={existing.id})")
                continue
            
            user = User(**user_data)
            session.add(user)
            await session.flush()
            print(f"✅ User created: {user_data['email']} (id={user.id})")
        
        await session.commit()
        print("✅ Seed complete")


async def main() -> None:
    print("🌱 Seeding database...")
    await seed_users()


if __name__ == "__main__":
    asyncio.run(main())
