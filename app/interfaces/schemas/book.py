from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class BookCreateSchema(BaseModel):
    title: str = Field(..., max_length=500)
    author: str = Field(..., max_length=255)
    description: Optional[str] = None


class BookUpdateSchema(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    author: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None


class BookReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    author: str
    description: Optional[str]
    created_at: datetime


class BookPaginatedSchema(BaseModel):
    items: list[BookReadSchema]
    total: int
    page: int
    page_size: int
    total_pages: int