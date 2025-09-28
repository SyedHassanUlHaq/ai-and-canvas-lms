from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import warnings
try:
    from pgvector.sqlalchemy import Vector
    HAS_VECTOR = True
except ImportError as e:
    HAS_VECTOR = False
    warnings.warn(f"pgvector not available: {e}. Using Text fallback.")
    
    # Create a fallback Vector class
    from sqlalchemy import TypeDecorator
    class Vector(TypeDecorator):
        impl = Text
        cache_ok = True



Base = declarative_base()

class ConversationMemory(Base):
    __tablename__ = "conversation_memory"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), nullable=False, index=True)
    user_name = Column(String(150), nullable=True)
    course_id = Column(String(50), nullable=False, index=True)
    module_item_id = Column(String(50), nullable=True)
    message = Column(Text, nullable=False)
    message_from = Column(String(10), default='user', nullable=False) 
    session_id = Column(String(100), nullable=False)
    embedding = Column(Vector(3072), nullable=False)  # matches all-MiniLM-L6-v2
    summary = Column(Text, nullable=True)
    # response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    # context_used = Column(Text, nullable=True)  # JSON string of context used
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_user_course_module', 'user_id', 'course_id', 'module_item_id'),
        Index('idx_timestamp', 'timestamp'),
    )


