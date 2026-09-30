from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class UserEntity:
    id: Optional[int]
    email: str
    hashed_password: str
    created_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
