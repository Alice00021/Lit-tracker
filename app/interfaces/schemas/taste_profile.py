from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Dict, Any, List, Optional


class TasteAnalysisSchema(BaseModel):
    themes: List[str] = []
    style: str = ""
    loves: List[str] = []
    dislikes: List[str] = []
    summary: str = ""


class TasteProfileReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    analysis: Dict[str, Any]
    entries_count: int
    status: str
    error: Optional[str] = None
    updated_at: datetime