from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, ForeignKey("customers.id"), index=True)
    channel = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    
    agent_id = Column(String, nullable=True)
    extracted_context = Column(JSON, default=dict)
    sentiment = Column(String, nullable=True)
    intent = Column(String, nullable=True)
    metadata = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
