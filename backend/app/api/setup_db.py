import os
import pathlib
from pydoc import doc
from fastapi import FastAPI, HTTPException, status, BackgroundTasks, APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
from typing import Optional

from app.services.huggingface_embeddings import embed_course_doc
# from app.repository.vector import CourseChunkRepository
from app.core.dependancies import get_db

# from repository.vector import CourseChunkRepository

# Initialize FastAPI app
# app = FastAPI(title="Course Chunks API", version="1.0.0")
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

# Thread pool for running background tasks
# executor = ThreadPoolExecutor(max_workers=1)

# @router.post("/", response_model=SetupResponse)
# async def setup_database_endpoint(
#     request: SetupRequest,
#     background_tasks: BackgroundTasks
# ):
#     """
#     Endpoint to setup database by loading chunks and generating embeddings.
#     This runs as a background task since it can take significant time.
#     """
#     global setup_status
    
#     # Check if setup is already in progress
#     if setup_status["in_progress"]:
#         raise HTTPException(
#             status_code=409,
#             detail="Database setup is already in progress"
#         )
    
#     # Reset status
#     setup_status = {
#         "in_progress": True,
#         "completed": False,
#         "error": None,
#         "chunks_processed": 0,
#         "total_chunks": 0,
#         "progress": 0.0
#     }
    
#     # Run setup in background
#     background_tasks.add_task(
#         run_setup_background,
#         request.chunks_file,
#         request.project_id
#     )
    
#     return JSONResponse(
#         status_code=202,
#         content={
#             "status": "accepted",
#             "message": "Database setup started in background",
#             "chunks_file": request.chunks_file,
#             "project_id": request.project_id
#         }
#     )

# def run_setup_background(chunks_file: str, project_id: str):
#     """Run the database setup in a background thread"""
#     global setup_status
    
#     try:
#         logger.info(f"Starting database setup with file: {chunks_file}")
        
#         # Handle file path - if it's not absolute, make it relative to the current directory
#         if not os.path.isabs(chunks_file):
#             chunks_file = str(CURRENT_DIR / chunks_file)
        
#         # Load chunks to get total count for progress tracking
#         try:
#             import json
#             with open(chunks_file, 'r') as f:
#                 chunks_data = json.load(f)
#             setup_status["total_chunks"] = len(chunks_data)
#             logger.info(f"Successfully loaded {len(chunks_data)} chunks from {chunks_file}")
#         except Exception as e:
#             logger.error(f"Error loading chunks file: {e}")
#             setup_status["error"] = f"Error loading chunks file: {str(e)}"
#             setup_status["in_progress"] = False
#             return
        
#         # Run the actual setup (this is your existing function)
#         success = setup_database(chunks_data)
        
#         if success:
#             setup_status["completed"] = True
#             setup_status["chunks_processed"] = setup_status["total_chunks"]
#             setup_status["progress"] = 100.0
#             logger.info("Database setup completed successfully")
#         else:
#             setup_status["error"] = "Database setup failed (check logs for details)"
#             logger.error("Database setup failed")
            
#     except Exception as e:
#         error_msg = f"Unexpected error during setup: {str(e)}"
#         setup_status["error"] = error_msg
#         logger.error(error_msg)
#     finally:
#         setup_status["in_progress"] = False
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException
import asyncpg
import json
from app.core.config import settings



async def insert_course_chunk(doc_name, module_name, content, embedding):
    conn = await asyncpg.connect(settings.connection_url)

    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    
    # Convert embedding list to array for Postgres
    await conn.execute(
        """
        INSERT INTO course_embeddings (doc_name, module_name, content, embedding)
        VALUES ($1, $2, $3, $4)
        """,
        doc_name,
        module_name,
        content,
        embedding_str  # asyncpg supports Postgres arrays for simple lists
    )
    
    await conn.close()

@router.post("/v2", status_code=status.HTTP_201_CREATED)
async def setup_database_endpoint(
    db: AsyncSession = Depends(get_db)
):
    # Handle file path - if it's not absolute, make it relative to the current directory
    # if not os.path.isabs('backend/app/api/course_chunks.json'):
    #     chunks_file = str(CURRENT_DIR / 'course_chunks.json')
    
    # Load chunks to get total count for progress tracking
    try:
        import json
        with open('app/api/course_chunks.json', 'r') as f:
            chunks_data = json.load(f)    
            # print('FILE READ: ', chunks_data)
        
        repo = CourseChunkRepository(db)
        chunks = []
        for chunk_data in chunks_data:
            print('chunk: ', chunk_data)
            if chunk_data['metadata']['chunk_type'] != 'content':
                print('SKIP!')
                continue
            else:
                doc_name=chunk_data['metadata']['item_name']
                module_name=chunk_data['metadata']['module_name']
                content=chunk_data['content'].replace('content:', '')

                print('doc_name, ', doc_name, 'module', module_name, 'content', content)
                obj = await embed_course_doc(str(content), str(doc_name), str(module_name))

                print('object: ', obj)
                # chunk_datas = CourseChunkCreate(**obj)  # Convert dict → Pydantic model
                # chunk = await repo.create(chunk_datas)
                a = await insert_course_chunk(doc_name, module_name, content, obj['embedding'])
                # chunk = await repo.create(obj)
                # chunk = CourseChunk(
                #     doc_name=obj['doc_name'],
                #     module_name=obj['module_name'],
                #     content=obj['content'],
                #     embedding=obj['embedding']
                # )
                # ch = await repo.create(chunk)
                print(a, 'enbedded')

        logger.info(f"✅ Loaded {len(chunks)} chunks")
        return {
            "status": "success",
            "message": "Course chunk created successfully",
        }


    except Exception as e:
        print(e)
        return {
            "status": "failed",
            "message": "Course chunk not created successfully",
            # "data": chunk  # or convert to dict if needed
        }

from typing import List, Dict

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

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
    
    print('hello world')

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



