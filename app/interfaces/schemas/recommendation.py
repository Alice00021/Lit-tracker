from pydantic import BaseModel
from typing import Optional


class RecommendedBookSchema(BaseModel):
    id: int
    title: str
    author: str
    description: Optional[str] = None


class RecommendationSchema(BaseModel):
    book: RecommendedBookSchema
    similarity: float
    reason: str


class RecommendationsResponseSchema(BaseModel):
    recommendations: list[RecommendationSchema]
    total: int