from sqlalchemy import Column, String
from app.models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"  # Явно указываем имя таблицы

    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "email": self.email,
        })
        return data