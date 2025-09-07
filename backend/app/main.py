"""
FastAPI application for AI Tutor Platform - Clean Version
Simplified for iframe widget flow - only essential endpoints
"""
import logging
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import json
import traceback
import os

from app.core.config import settings
from app.core.canvas_config_rce import canvas_settings
from app.services.ai_service_rce import ai_service
from app.services.database_service_rce import database_service
from app.canvas.canvas_service_rce import canvas_service
from app.services.widget_ai_service_rce import widget_ai_service
from app.services.summarize_conversation import summary_creator
from app.repository.conversation_rce import ConversationMemoryRawRepository_rce
from app.api.lti import model
from fastapi import Depends
from app.core.dependancies import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    debug=settings.debug
)

# Add global exception handler for validation errors
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(
    settings.connection_url,
    echo=settings.debug,
    future=True  # Add this for async support
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors and log them"""
    logger.error(f"❌ Request validation error: {exc}")
    logger.error(f"❌ Request body: {await request.body()}")
    logger.error(f"❌ Validation errors: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": exc.errors()}
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    course_id: Optional[str] = None
    module_id: Optional[str] = None
    page_id: Optional[str] = None
    page_slug: Optional[str] = None
    module_item_id: Optional[str] = None
    language: Optional[str] = None
    session_id: Optional[str] = None
    
    # Enhanced context from database
    module_context: Optional[Dict[str, Any]] = None
    page_content: Optional[str] = None
    page_title: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    context_used: List[Dict[str, Any]]
    confidence: str
    total_context_docs: int
    insights: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    quiz_data: Optional[Dict[str, Any]] = None
    
    # Additional fields for enhanced responses
    source: Optional[str] = None 
    timestamp: Optional[str] = None

# Health check endpoint
@app.get("/health")
def health():
    """Health check endpoint"""
    try:
        # For Cloud Run deployment, skip database health check temporarily
        if os.getenv("ENVIRONMENT") == "production":
            return {
                "status": "ok",
                "service": "ai_tutor_api",
                "environment": settings.environment,
                "database": "skipped_in_production",
                "note": "Database health check disabled for Cloud Run deployment"
            }
        
        # Local development - check database
        db_health = database_service.health_check()
        
        return {
            "status": "ok",
            "service": "ai_tutor_api",
            "environment": settings.environment,
            "database": db_health
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "service": "ai_tutor_api",
            "environment": settings.environment,
            "error": str(e)
        }

# Core chat endpoint
@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)) -> Any:
    logger.info("🚀 Chat endpoint reached - request validation passed!")
    
    # Log the incoming request for debugging
    logger.info(f"🔍 Chat request received:")
    logger.info(f"  - Message: {request.message[:100]}...")
    logger.info(f"  - User ID: {request.user_id}")
    logger.info(f"  - Course ID: {request.course_id}")
    logger.info(f"  - Module Item ID: {request.module_item_id}")
    logger.info(f"  - Page Content: {'Yes' if request.page_content else 'No'}")
    logger.info(f"  - Module Context: {'Yes' if request.module_context else 'No'}")
    logger.info(f"  - Session ID: {request.session_id}")
    
    # Also log the raw request body for debugging
    try:
        body = await http_request.body()
        logger.info(f"🔍 Raw request body: {body.decode('utf-8', errors='ignore')[:500]}")
    except Exception as e:
        logger.info(f"🔍 Could not read raw body: {e}")
    
    # Detect user's language preference from message content
    detected_language = ai_service.detect_user_language(request.message)
    
    try:
        
        # Get relevant context based on request parameters
        context_docs = []
        
        # Priority 1: Use database content if available (most accurate)
        if request.page_content and request.module_context:
            logger.info(f"🔍 Using database content for module item {request.module_item_id}")
            logger.info(f"📋 Module: {request.module_context.get('module_name', 'Unknown')}")
            logger.info(f"📄 Item: {request.module_context.get('item_title', 'Unknown')}")
            logger.info(f"📊 Content length: {len(request.page_content)} characters")
            
            # Create context document from database content
            context_docs = [{
                "title": request.page_title or request.module_context.get('item_title', 'Course Content'),
                "content": request.page_content,
                "content_type": "page_content",
                "source": "database",
                "relevance_score": 100.0,
                "metadata": {
                    "module_name": request.module_context.get('module_name'),
                    "module_position": request.module_context.get('module_position'),
                    "item_title": request.module_context.get('item_title'),
                    "item_type": request.module_context.get('item_type'),
                    "item_position": request.module_context.get('item_position'),
                    "yt_transcript": request.module_context.get('yt_transcript')
                }
            }]
            
            logger.info(f"✅ Created context from database content")
            
        elif request.module_item_id and request.course_id:
            # Priority 2: Fallback to basic context if database content not available
            logger.info(f"🔍 No database content available for module item {request.module_item_id}")
            logger.info(f"⚠️ Using minimal context - recommend refreshing the page")
            
            # Create minimal context for fallback
            context_docs = [{
                "title": "Course Context",
                "content": f"Course {request.course_id}, Module Item {request.module_item_id}",
                "content_type": "fallback",
                "source": "fallback",
                "relevance_score": 50.0
            }]
            
            logger.info(f"📚 Created fallback context for module item {request.module_item_id}")
        elif request.page_slug and request.course_id:
            # Page-specific context - minimal fallback
            logger.info(f"🔍 No database content available for page {request.page_slug}")
            context_docs = [{
                "title": "Page Context",
                "content": f"Page {request.page_slug} in course {request.course_id}",
                "content_type": "fallback",
                "source": "fallback",
                "relevance_score": 50.0
            }]
        elif request.course_id:
            # Course-level context - minimal fallback
            logger.info(f"🔍 No database content available for course {request.course_id}")
            context_docs = [{
                "title": "Course Context",
                "content": f"Course {request.course_id} - general information",
                "content_type": "fallback",
                "source": "fallback",
                "relevance_score": 50.0
            }]
            
            
        
        # Generate AI response - use widget AI service if database content available
        if request.page_content and request.module_context:
            # Use specialized widget AI service with Gemini for database content
            logger.info("🤖 Using Widget AI Service with Gemini for database content")
            
            repo = ConversationMemoryRawRepository_rce(db)
        
            query_embedding = model.encode(request.message, convert_to_numpy=True, device='cpu').tolist()
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            summary=None
            history = []
            similar_convo = 'None'
            exists = await repo.get_by_session_id(session_id=request.session_id)
            if not exists:
            
                params = {
                'user_id': None,
                'course_id': None,
                'module_item_id': None,
                'message': request.message,
                'message_from': 'user',
                'session_id': request.session_id,
                'summary': None,
                'embedding': embedding_str
                # 'context_used': json.dumps(memory_data.get('context_used')) if memory_data.get('context_used') else None
                }   
                
                await repo.create(params)
            else:
                similar_convo = await repo.find_similar_conversations(session_id=request.session_id, embedding=embedding_str)
                summary = await repo.get_latest_summary(session_id=request.session_id)
                history = await repo.format_conversations_for_chatbot(session_id=request.session_id)
                
                
            
            
            
            # Prepare user context
            user_context = {
                "course_id": request.course_id,
                "module_context": request.module_context
            }
            
            logger.info(f"🔍 Calling widget_ai_service.generate_response with context_docs: {len(context_docs)}")
            ai_response_dict = widget_ai_service.generate_response(
                message=request.message,
                context_docs=context_docs,
                language=detected_language,
                user_context=user_context,
                summary=summary,
                similar_convo=similar_convo,
                history=history
            )
            
            background_tasks.add_task(summary_creator.summerize, None, request.message, ai_response_dict.get("reply", ""), summary, request.session_id, repo)
            
            # new_summary = await summary_creator.summerize(query=request.message, response=ai_response_dict.get("reply", ""), summary=summary, session_id=request.session_id, repo=repo)
            
            logger.info(f"✅ Widget AI service response: {ai_response_dict.get('reply', '')[:100]}...")
            logger.info(f"🔍 Response source: {ai_response_dict.get('source', 'unknown')}")
            
            # Add memory-related fields for compatibility
            ai_response_dict["insights"] = None
            
        else:
            # Use regular AI service for knowledge base content
            logger.info("🤖 Using regular AI service for knowledge base content")
            ai_response_dict = ai_service.generate_response(
                message=request.message,
                context_docs=context_docs,
                language=detected_language,
                course_id=request.course_id
            )
            
            # logger.info(f"✅ Regular AI service response: {ai_response_dict.get('reply', '')[:100]}...")
        

        # Convert dictionary response to ChatResponse object
        ai_response = ChatResponse(
            reply=ai_response_dict.get("reply", ""),
            context_used=ai_response_dict.get("context_used", []),
            confidence=ai_response_dict.get("confidence", "low"),
            total_context_docs=ai_response_dict.get("total_context_docs", 0),
            insights=ai_response_dict.get("insights"),
            error=ai_response_dict.get("error"),
            source=ai_response_dict.get("source"),
            timestamp=ai_response_dict.get("timestamp")
        )
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            reply=f"Sorry, I encountered an error: {str(e)}",
            context_used=[],
            confidence="low",
            total_context_docs=0,
            error=str(e)
        )


# Widget endpoints
@app.get("/ai-tutor")
def ai_tutor_widget():
    """AI Tutor Widget - Main iframe endpoint"""
    try:
        with open("app/widgets/ai_tutor_widget.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Error serving AI tutor widget: {e}")
        return HTMLResponse(content=f"<h1>Error loading widget: {str(e)}</h1>", status_code=500)

@app.get("/api/v1/canvas/course/{course_id}/module-item-sequence")
async def get_module_item_sequence(course_id: str, asset_type: str = Query(...), asset_id: str = Query(...)):
    """Get module item sequence from Canvas API"""
    try:
        logger.info(f"🔍 Getting module item sequence for course {course_id}, asset_type: {asset_type}, asset_id: {asset_id}")
        
        # Call Canvas service to get module item sequence
        sequence_data = canvas_service.get_module_item_sequence(course_id, asset_type, asset_id)
        
        if not sequence_data:
            logger.warning(f"⚠️ No module item sequence found for course {course_id}, asset_type: {asset_type}, asset_id: {asset_id}")
            return {
                "status": "success",
                "items": [],
                "message": "No module items found"
            }
        
        logger.info(f"✅ Retrieved module item sequence with {len(sequence_data.get('items', []))} items")
        
        return {
            "status": "success",
            "items": sequence_data.get('items', []),
            "modules": sequence_data.get('modules', []),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"💥 Error in get_module_item_sequence: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/ai/status")
def get_ai_status():
    """Get AI service status"""
    try:
        return {
            "status": "success",
            "ai_service": "operational",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting AI status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Include content router
from app.api.content_rce import router as content_router
app.include_router(content_router)

# Include LTI router
from app.api.lti_rce import router as lti_router
app.include_router(lti_router)


from app.api.lti import router as lti_router
app.include_router(lti_router)

from app.api.setup_db import router as db_router
app.include_router(db_router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")