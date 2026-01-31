from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, ForeignKey("customers.id"), index=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="open")
    priority = Column(String, default="medium")
    
    metadata = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
