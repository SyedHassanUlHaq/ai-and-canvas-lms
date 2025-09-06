from sqlalchemy import Column, String, Text, DateTime, Integer, MetaData
from sqlalchemy.dialects.postgresql import VARCHAR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
# from pgvector.sqlalchemy import Vector  # Import Vector from pgvector.sqlalchemy, 

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


# Base = declarative_base()
Base = declarative_base(metadata=MetaData(schema="public"))

# from pgvector.sqlalchemy import Vector

# Base = declarative_base()


class CourseEmbeddings(Base):
    __tablename__ = "course_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_name = Column(String, nullable=False)
    module_name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384))  # matches all-MiniLM-L6-v2
    # created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<CourseChunk(id={self.id}, doc_name='{self.doc_name}', module='{self.module_name}')>"
