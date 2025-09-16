import os
import pathlib
from pydoc import doc
from fastapi import HTTPException, status, APIRouter
from pydantic import BaseModel
import logging
from typing import Optional

from app.services.huggingface_embeddings import embed_course_doc
from app.core.dependancies import get_db


router = APIRouter(prefix="/setupdb", tags=["LTI 1.3"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the directory where this file is located
CURRENT_DIR = pathlib.Path(__file__).parent
DEFAULT_CHUNKS_FILE = str(CURRENT_DIR / "course_chunks.json")

# Pydantic models for request/response
class SetupRequest(BaseModel):
    chunks_file: str = DEFAULT_CHUNKS_FILE
    project_id: str = "elivision-ai-1"

class SetupResponse(BaseModel):
    status: str
    message: str
    chunks_processed: Optional[int] = None
    error: Optional[str] = None

class StatusResponse(BaseModel):
    status: str
    message: str
    progress: Optional[float] = None
    chunks_processed: Optional[int] = None
    total_chunks: Optional[int] = None

# Global variables to track setup progress
setup_status = {
    "in_progress": False,
    "completed": False,
    "error": None,
    "chunks_processed": 0,
    "total_chunks": 0,
    "progress": 0.0
}


from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException



async def insert_course_chunk(db: AsyncSession, doc_name: str, module_name: str, content: str, embedding):
    # Convert embedding list to PostgreSQL array format
    # embedding_array = "{" + ",".join(str(x) for x in embedding) + "}"
    
    # Use SQLAlchemy core for async execution with raw SQL
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    
    stmt = text("""
        INSERT INTO course_embeddings (doc_name, module_name, content, embedding)
        VALUES (:doc_name, :module_name, :content, :embedding)
    """)

    params = {
            'doc_name': doc_name,
            'module_name': module_name,
            'content': content,
            'embedding': embedding_str
            # 'context_used': json.dumps(memory_data.get('context_used')) if memory_data.get('context_used') else None
        }
        
    result = await db.execute(stmt, params)
    
    # stmt = stmt.bindparams(
    #     doc_name=doc_name,
    #     module_name=module_name,
    #     content=content,
    #     embedding=embedding_str
    # )
    await db.commit()
    
    # await db.execute(stmt)
    # await db.commit()

@router.post("/v2", status_code=status.HTTP_201_CREATED)
async def setup_database_endpoint(
    db: AsyncSession = Depends(get_db)
):
    try:
        import json
        with open('app/api/course_chunks.json', 'r') as f:
            chunks_data = json.load(f)
            logger.debug('FILE READ: %s', chunks_data)
        
        count = 0
        for chunk_data in chunks_data:
            logger.debug('chunk: %s', chunk_data)
            if chunk_data['metadata']['chunk_type'] != 'content':
                logger.debug('SKIP! Non-content chunk type')
                continue
            else:
                doc_name = chunk_data['metadata']['item_name']
                module_name = chunk_data['metadata']['module_name']
                content = chunk_data['content'].replace('content:', '')

                logger.debug('Processing - doc_name: %s, module: %s, content: %s', doc_name, module_name, content[:30])  
                obj = await embed_course_doc(str(content), str(doc_name), str(module_name))

                logger.debug('Embedding object: %s', obj)

                # Pass the db session to the insert function
                await insert_course_chunk(db, doc_name, module_name, content, obj['embedding'])

                logger.info('Embedded document: %s', doc_name)
                count += 1

        logger.info(f"✅ Loaded {count} chunks")
        return {
            "status": "success",
            "message": f"Successfully loaded {count} course chunks",
        }

    except Exception as e:
        logger.error("Failed to setup database: %s", e, exc_info=True)
        # Rollback in case of error
        await db.rollback()
        return {
            "status": "failed",
            "message": "Course chunks not created successfully",
        }
from typing import List, Dict

from sqlalchemy import text

@router.get("/course_chunks/")
async def get_course_chunks(db: AsyncSession = Depends(get_db)):
    try:
        # Using SQLAlchemy core approach (similar to your original query)
        result = await db.execute(
            text("SELECT id, doc_name, module_name, content, embedding FROM course_embeddings LIMIT 50")
        )
        print(result)
        
        # Convert to list of dictionaries
        chunks = []
        for row in result:
            chunks.append({
                "id": row.id,
                "doc_name": row.doc_name,
                "module_name": row.module_name,
                "content": row.content,
                "embedding": row.embedding
            })
        
        return chunks
        
    except Exception as e:
        # Handle any database errors
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

from sentence_transformers import SentenceTransformer

# Initialize embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")



async def get_top_5_content(query: str, db: AsyncSession) -> List[Dict]:
    """
    Get top 5 matching content from course_embeddings using SQLAlchemy async and pgvector.
    """
    # 1️⃣ Encode query to vector
    query_embedding = model.encode(query, convert_to_numpy=True, device='cpu').tolist()
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    


    try:
        # 2️⃣ Use SQLAlchemy with pgvector distance operator
        # Note: SQLAlchemy doesn't have built-in support for pgvector operators,
        # so we use text() for the distance calculation
        sql = text("""
            SELECT id, doc_name, module_name, content, embedding
            FROM course_embeddings
            ORDER BY embedding <=> :embedding
            LIMIT 5
        """)
        
        result = await db.execute(sql, {"embedding": embedding_str})
        rows = result.mappings().all()
        
        # Convert to list of dictionaries and handle embedding serialization
        results = []
        for row in rows:
            row_dict = dict(row)
            # Ensure embedding is JSON serializable
            embedding = row_dict['embedding']
            if hasattr(embedding, 'tolist'):
                row_dict['embedding'] = embedding.tolist()
            results.append(row_dict)
        
        return results
        
    except Exception as e:
        print(f"Error in get_top_5_content: {e}")
        raise



