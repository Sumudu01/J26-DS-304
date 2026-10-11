from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NotificationCreate(BaseModel):
    type: str = Field(default="system", min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)

    @field_validator("type", "title", "body")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Notification values cannot be blank")
        return normalized


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    body: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
