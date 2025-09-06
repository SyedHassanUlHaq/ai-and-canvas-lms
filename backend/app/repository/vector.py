# from typing import List, Dict, Any, Optional
# from sqlalchemy import create_engine, text
# from sqlalchemy.orm import sessionmaker
# import logging
# from pgvector.sqlalchemy import Vector
# import numpy as np
# from app.models.vector import CourseEmbeddings
# from app.core.config import Settings
# from sqlalchemy.orm import Session
# from sqlalchemy.future import select

# logger = logging.getLogger(__name__)

# # class CourseChunkRepository:
# #     def __init__(self, connection_string: str = Settings.connection_url):
# #         self.engine = create_engine(connection_string)
# #         self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
# #     def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
# #         """Add chunks and their embeddings to the database"""
# #         try:
# #             with self.SessionLocal() as session:
# #                 # Clear existing data (optional - remove if you want to append)
# #                 # session.execute(text("DELETE FROM course_chunks"))
                
# #                 # Insert chunks with embeddings
# #                 for chunk_data, embedding in zip(chunks, embeddings):
# #                     chunk = CourseChunk(
# #                         id=chunk_data['id'],
# #                         content=chunk_data['content'],
# #                         content_metadata=chunk_data['content_metadata'],
# #                         chunk_type=chunk_data['chunk_type'],
# #                         parent_id=chunk_data.get('parent_id'),
# #                         related_ids=chunk_data.get('related_ids', []),
# #                         embedding=embedding
# #                     )
# #                     session.add(chunk)
                
# #                 session.commit()
# #                 logger.info(f"✅ Added {len(chunks)} chunks to database")
                
# #         except Exception as e:
# #             logger.error(f"❌ Error adding chunks: {e}")
# #             raise
    
# #     def search_similar_chunks(self, query_embedding: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
# #         """Search for similar chunks using cosine similarity"""
# #         try:
# #             with self.SessionLocal() as session:
# #                 # Convert query embedding to numpy array for pgvector
# #                 embedding_array = np.array(query_embedding)
                
# #                 # Use SQLAlchemy's ORM with pgvector similarity search
# #                 results = session.query(
# #                     CourseChunk.id,
# #                     CourseChunk.content,
# #                     CourseChunk.content_metadata,
# #                     CourseChunk.chunk_type,
# #                     CourseChunk.parent_id,
# #                     CourseChunk.related_ids,
# #                     (1 - CourseChunk.embedding.cosine_distance(embedding_array)).label('similarity')
# #                 ).order_by(
# #                     CourseChunk.embedding.cosine_distance(embedding_array)
# #                 ).limit(top_k).all()
                
# #                 # Convert results to dictionaries
# #                 return [{
# #                     # 'id': result.id,
# #                     'content': result.content,
# #                     # 'metadata': result.content_metadata,
# #                     # 'chunk_type': result.chunk_type,
# #                     # 'parent_id': result.parent_id,
# #                     # 'related_ids': result.related_ids,
# #                     'similarity': float(result.similarity)
# #                 } for result in results]
                
# #         except Exception as e:
# #             logger.error(f"❌ Error searching similar chunks: {e}")
# #             return []
# from sqlalchemy.ext.asyncio import AsyncSession
# from fastapi import Depends, HTTPException
# # from app.core.dependancies import get_db

# from fastapi import Depends
# from sqlalchemy.ext.asyncio import AsyncSession
# from typing import AsyncGenerator
# from app.main import AsyncSessionLocal
# from app.core.dependancies import get_db 

# from pydantic import BaseModel, Field
# from datetime import datetime


# # # In your repository or route
# # async def get_db() -> AsyncGenerator[AsyncSession, None]:
# #     async with AsyncSessionLocal() as session:
# #         try:
# #             yield session
# #         finally:
# #             await session.close()

# class CourseChunkBase(BaseModel):
#     doc_name: str = Field(..., description="Document name", example="math_101.pdf")
#     module_name: str = Field(..., description="Module name", example="Algebra")
#     content: str = Field(..., description="Course content", example="Introduction to algebraic equations")
#     embedding: Optional[List[float]] = Field(None, description="Vector embedding", example=[0.1, 0.2, 0.3])

# # Schema for creating new chunks (without ID and timestamps)
# class CourseChunkCreate(CourseChunkBase):
#     pass

# # Schema for updating chunks (all fields optional)
# class CourseChunkUpdate(BaseModel):
#     doc_name: Optional[str] = Field(None, description="Document name")
#     module_name: Optional[str] = Field(None, description="Module name")
#     content: Optional[str] = Field(None, description="Course content")
#     embedding: Optional[List[float]] = Field(None, description="Vector embedding")

# # Schema for response (includes ID and timestamps)
# class CourseChunkResponse(CourseChunkBase):
#     id: int = Field(..., description="Unique identifier")
#     created_at: datetime = Field(..., description="Creation timestamp")
    
#     class Config:
#         from_attributes = True  # Allows ORM mode for SQLAlchemy objects


# class CourseChunkRepository:
#     def __init__(self, db: AsyncSession = Depends(get_db)):  # FastAPI injects the session):
#         self.db = db

#     async def create(self, chunk_data: CourseChunkCreate) -> CourseEmbeddings:
#         """Create a new course chunk from schema data."""
#         chunk = CourseEmbeddings(**chunk_data.model_dump())
#         self.db.add(chunk)
#         await self.db.commit()
#         await self.db.refresh(chunk)
#         return chunk

#     async def get_all(self) -> List[CourseEmbeddings]:
#         """Get all course chunks."""
#         result = await self.db.execute(select(CourseEmbeddings))
#         return result.scalars().all()

#     async def search_by_embedding(self, query_embedding: List[float], limit: int = 5) -> List[CourseEmbeddings]:
#         """Search for similar course chunks using vector similarity."""
#         # This assumes your database supports vector similarity search (e.g., pgvector)
#         # Replace with your actual similarity search logic
#         result = await self.db.execute(
#             select(CourseEmbeddings)
#             .order_by(CourseEmbeddings.embedding.cosine_distance(query_embedding))
#             .limit(limit)
#         )
#         return result.scalars().all()
    
#     # def get_chunk_by_id(self, chunk_id: str) -> Optional[CourseChunk]:
#     #     """Get a specific chunk by ID"""
#     #     try:
#     #         with self.SessionLocal() as session:
#     #             return session.query(CourseChunk).filter(CourseChunk.id == chunk_id).first()
#     #     except Exception as e:
#     #         logger.error(f"❌ Error getting chunk by ID: {e}")
#     #         return None
    
#     # def get_related_chunks(self, chunk_id: str) -> List[CourseChunk]:
#     #     """Get chunks related to a specific chunk"""
#     #     try:
#     #         with self.SessionLocal() as session:
#     #             chunk = session.query(CourseChunk).filter(CourseChunk.id == chunk_id).first()
#     #             if chunk and chunk.related_ids:
#     #                 return session.query(CourseChunk).filter(CourseChunk.id.in_(chunk.related_ids)).all()
#     #             return []
#     #     except Exception as e:
#     #         logger.error(f"❌ Error getting related chunks: {e}")
#     #         return []
    
#     # def get_chunks_by_type(self, chunk_type: str, limit: int = 10) -> List[CourseChunk]:
#     #     """Get chunks by type"""
#     #     try:
#     #         with self.SessionLocal() as session:
#     #             return session.query(CourseChunk).filter(CourseChunk.chunk_type == chunk_type).limit(limit).all()
#     #     except Exception as e:
#     #         logger.error(f"❌ Error getting chunks by type: {e}")
#     #         return []