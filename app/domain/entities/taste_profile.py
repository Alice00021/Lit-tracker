from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class TasteProfileEntity:
    id: Optional[int]
    user_id: int
    analysis: Dict[str, Any]
    entries_count: int
    status: str = "pending"
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None