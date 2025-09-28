"""
Content API for retrieving module item content from PostgreSQL database
Handles the /api/v1/content/module-item/{module_item_id} endpoint
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/content", tags=["content"])

# Import database configuration
from app.core.config import settings
from app.services.db_config_rce import get_database_connection

# Response models
class ModuleItemContent(BaseModel):
    module_id: int
    module_name: str
    module_position: int
    item_title: str
    item_type: str
    item_position: int
    page_content: Optional[str] = None
    page_title: Optional[str] = None
    yt_transcript: Optional[str] = None

class ContentResponse(BaseModel):
    status: str
    content: Optional[ModuleItemContent] = None
    message: Optional[str] = None

def get_db_session():
    """Get database session using existing database configuration"""
    try:
        connection = get_database_connection()
        if not connection:
            raise HTTPException(status_code=500, detail="Database connection failed")
        return connection
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

@router.get("/module-item/{module_item_id}", response_model=ContentResponse)
async def get_module_item_content(module_item_id: int):
    """Get module item content from database"""
    try:
        connection = get_db_session()
        query = """
            SELECT 
                m.id as module_id, m.name as module_name, m.position as module_position,
                mi.title as item_title, mi.item_type, mi.position as item_position,
                p.body as page_content, p.title as page_title,
                p.yt_transcript as yt_transcript
            FROM modules m
            JOIN module_items mi ON m.id = mi.module_id
            LEFT JOIN pages p ON mi.id = p.module_item_id
            WHERE mi.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(query, (module_item_id,))
            row = cursor.fetchone()
        
        if row:
            content = ModuleItemContent(
                module_id=row['module_id'],
                module_name=row['module_name'],
                module_position=row['module_position'],
                item_title=row['item_title'],
                item_type=row['item_type'],
                item_position=row['item_position'],
                page_content=row['page_content'],
                page_title=row['page_title'],
                yt_transcript=row['yt_transcript']
            )
            
            logger.info("jkfsdhkjfsdjkfnsdjkfnjksdnfjksdnjkf \n\n\n\n\n\n", content)
            return ContentResponse(status="success", content=content)
        else:
            return ContentResponse(status="error", message="Module item not found")
            
    except Exception as e:
        logger.error(f"Error getting module item content: {e}")
        return ContentResponse(status="error", message=str(e))
    finally:
        if 'connection' in locals():
            connection.close()

@router.get("/health")
async def content_health_check():
    """Health check for content API"""
    return {"status": "healthy", "service": "content_api"} 