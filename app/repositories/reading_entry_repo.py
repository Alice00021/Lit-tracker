from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import List

async def get_by_user_id(self, user_id: int, limit: int = 100, offset: int = 0):
    stmt = (
        select(ReadingEntry)
        .where(ReadingEntry.user_id == user_id)
        .order_by(desc(ReadingEntry.read_date))
        .offset(offset)
        .limit(limit)
        .options(selectinload(ReadingEntry.book))
    )
    result = await self.session.execute(stmt)
    return result.scalars().all()