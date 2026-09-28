from pydantic import BaseModel, Field


class SmartSearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Запрос в свободной форме",
        examples=["хочу что-то грустное про потерю, но не слишком тяжёлое"],
    )

class SmartSearchResponse(BaseModel):
    query: str
    answer: str = Field(..., description="Ответ LLM с объяснением")