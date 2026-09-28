from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.db import Base


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(200), nullable=False)

    description = Column(Text, nullable=False)

    category = Column(String(100), nullable=False, default="Other")

    status = Column(
        String(50),
        nullable=False,
        default="Reported"
    )

    priority = Column(
        String(50),
        nullable=False,
        default="Medium"
    )

    location = Column(String(300), nullable=True)

    latitude = Column(Float, nullable=True)

    longitude = Column(Float, nullable=True)

    image_path = Column(String(500), nullable=True)

    ai_summary = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )