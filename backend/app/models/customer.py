from sqlalchemy import Column, String, DateTime, Float, JSON
from sqlalchemy.sql import func
from app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    phone = Column(String, nullable=True)
    
    preferences = Column(JSON, default=dict)
    pain_points = Column(JSON, default=list)
    key_memories = Column(JSON, default=list)
    relationship_score = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
