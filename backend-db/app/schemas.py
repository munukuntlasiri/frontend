from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class IssueCreate(BaseModel):
    title: str
    description: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class IssueUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None


class IssueResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    status: str
    priority: str
    location: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    image_path: Optional[str]
    ai_summary: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)