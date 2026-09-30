"""
Seed-скрипт: демо-пользователи для локального запуска.
Запуск: python -m scripts.seed

Пароль демо-пользователей: Demo1234!  (только для локальной разработки!)
Скрипт идемпотентный; старым пользователям с заглушкой вместо хеша ставит настоящий хеш.
"""
import asyncio

from common import PasswordService
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import User

DEMO_PASSWORD = "Demo1234!"
LEGACY_PLACEHOLDER = "not-a-real-hash-just-for-test"
DEMO_EMAILS = ["alice@example.com", "bob@example.com"]


async def seed_users() -> None:
    async with AsyncSessionLocal() as session:
        for email in DEMO_EMAILS:
            result = await session.execute(select(User).where(User.email == email))
            existing = result.scalar_one_or_none()

            if existing:
                if existing.hashed_password == LEGACY_PLACEHOLDER:
                    existing.hashed_password = PasswordService.hash_password(DEMO_PASSWORD)
                    print(f"🔑 Password set for {email} (id={existing.id})")
                else:
                    print(f"⏭️  User {email} already exists (id={existing.id})")
                continue

            user = User(email=email, hashed_password=PasswordService.hash_password(DEMO_PASSWORD))
            session.add(user)
            await session.flush()
            print(f"✅ User created: {email} (id={user.id})")

        await session.commit()
        print("✅ Seed complete")


async def main() -> None:
    print("🌱 Seeding database...")
    await seed_users()


if __name__ == "__main__":
    asyncio.run(main())
