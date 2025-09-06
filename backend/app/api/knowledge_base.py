from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from app.services.knowledge_base_service import knowledge_base_service
from app.canvas.canvas_service import canvas_service
from app.core.config import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge-base", tags=["Knowledge Base"])

# Knowledge Base Sync Endpoints

@router.post("/sync/course/{course_id}")
async def sync_course_content(course_id: str):
    """Sync all content for a specific course from Canvas"""
    try:
        logger.info(f"🔄 Starting content sync for course {course_id}")
        
        # Validate course exists in Canvas
        course_info = canvas_service.get_course_info(course_id)
        if not course_info:
            raise HTTPException(status_code=404, detail=f"Course {course_id} not found in Canvas")
        
        # Start sync process
        sync_results = knowledge_base_service.sync_course_content(course_id)
        
        if "error" in sync_results:
            raise HTTPException(status_code=500, detail=sync_results["error"])
        
        return {
            "status": "success",
            "message": f"Course {course_id} content synced successfully",
            "results": sync_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error syncing course content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync course content: {str(e)}")

@router.post("/sync/all-courses")
async def sync_all_courses():
    """Sync content for all available courses"""
    try:
        logger.info("🔄 Starting sync for all courses")
        
        # Get all courses from Canvas
        courses = canvas_service.get_all_courses()
        if not courses:
            raise HTTPException(status_code=404, detail="No courses found in Canvas")
        
        sync_results = {}
        total_synced = 0
        
        for course in courses:
            try:
                course_id = str(course["id"])
                logger.info(f"🔄 Syncing course {course_id}: {course.get('name', 'Unknown')}")
                
                result = knowledge_base_service.sync_course_content(course_id)
                sync_results[course_id] = result
                
                if "error" not in result:
                    total_synced += 1
                    
            except Exception as e:
                logger.error(f"❌ Error syncing course {course.get('id', 'Unknown')}: {e}")
                sync_results[str(course.get("id", "unknown"))] = {"error": str(e)}
        
        return {
            "status": "success",
            "message": f"Synced {total_synced} out of {len(courses)} courses",
            "total_courses": len(courses),
            "successfully_synced": total_synced,
            "results": sync_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error syncing all courses: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync all courses: {str(e)}")

# Knowledge Base Search Endpoints

@router.get("/search")
async def search_knowledge_base(
    query: str = Query(..., description="Search query"),
    course_id: Optional[str] = Query(None, description="Filter by course ID"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    max_results: int = Query(10, ge=1, le=100, description="Maximum number of results")
):
    """Search knowledge base for relevant content"""
    try:
        logger.info(f"🔍 Searching knowledge base for: '{query}'")
        
        results = knowledge_base_service.search_knowledge_base(
            query=query,
            course_id=course_id,
            content_type=content_type,
            max_results=max_results
        )
        
        return {
            "status": "success",
            "query": query,
            "total_results": len(results),
            "results": results,
            "filters": {
                "course_id": course_id,
                "content_type": content_type,
                "max_results": max_results
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error searching knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/content/{content_id}")
async def get_knowledge_content(content_id: int):
    """Get specific knowledge content by ID"""
    try:
        logger.info(f"📖 Getting knowledge content {content_id}")
        
        content = knowledge_base_service.get_knowledge_content(content_id)
        if not content:
            raise HTTPException(status_code=404, detail=f"Knowledge content {content_id} not found")
        
        return {
            "status": "success",
            "content": content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting knowledge content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get content: {str(e)}")

# Knowledge Base Management Endpoints

@router.get("/course/{course_id}/summary")
async def get_course_knowledge_summary(course_id: str):
    """Get summary of knowledge base for a course"""
    try:
        logger.info(f"📊 Getting knowledge summary for course {course_id}")
        
        summary = knowledge_base_service.get_course_knowledge_summary(course_id)
        
        if "error" in summary:
            raise HTTPException(status_code=500, detail=summary["error"])
        
        return {
            "status": "success",
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting course knowledge summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")

@router.get("/stats")
async def get_knowledge_base_stats():
    """Get overall knowledge base statistics"""
    try:
        logger.info("📊 Getting knowledge base statistics")
        
        session = knowledge_base_service.get_session()
        
        try:
            from app.models.knowledge_base import Course, Module, ModuleItem, Page, Assignment, KnowledgeContent
            # Get total counts
            total_courses = session.query(Course).count()
            total_modules = session.query(Module).count()
            total_pages = session.query(Page).count()
            total_assignments = session.query(Assignment).count()
            total_knowledge_content = session.query(KnowledgeContent).count()
            
            # Get content by type
            content_by_type = session.query(
                KnowledgeContent.content_type,
                session.query(KnowledgeContent).count()
            ).group_by(KnowledgeContent.content_type).all()
            
            # Get recent activity
            recent_content = session.query(
                KnowledgeContent
            ).order_by(
                KnowledgeContent.last_accessed.desc()
            ).limit(5).all()
            
            stats = {
                "total_courses": total_courses,
                "total_modules": total_modules,
                "total_pages": total_pages,
                "total_assignments": total_assignments,
                "total_knowledge_content": total_knowledge_content,
                "content_by_type": {ct: count for ct, count in content_by_type},
                "recent_activity": [
                    {
                        "id": content.id,
                        "title": content.title,
                        "content_type": content.content_type,
                        "last_accessed": content.last_accessed.isoformat(),
                        "access_count": content.access_count
                    }
                    for content in recent_content
                ]
            }
            
            return {
                "status": "success",
                "stats": stats
            }
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Error getting knowledge base stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

# Content Type Endpoints

@router.get("/content-types")
async def get_content_types():
    """Get available content types in the knowledge base"""
    try:
        content_types = [
            "course",
            "module", 
            "module_item",
            "page",
            "assignment"
        ]
        
        return {
            "status": "success",
            "content_types": content_types
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting content types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get content types: {str(e)}")

@router.get("/courses")
async def get_courses():
    """Get all courses in the knowledge base"""
    try:
        session = knowledge_base_service.get_session()
        
        try:
            from app.models.knowledge_base import Course
            courses = session.query(Course).all()
            
            course_list = [
                {
                    "id": course.id,
                    "canvas_id": course.canvas_id,
                    "name": course.name,
                    "description": course.description,
                    "status": course.status,
                    "created_at": course.created_at.isoformat(),
                    "updated_at": course.updated_at.isoformat()
                }
                for course in courses
            ]
            
            return {
                "status": "success",
                "total_courses": len(course_list),
                "courses": course_list
            }
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Error getting courses: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get courses: {str(e)}")

# Health Check Endpoint

@router.get("/health")
async def knowledge_base_health():
    """Check knowledge base service health"""
    try:
        # Test database connection
        session = knowledge_base_service.get_session()
        
        try:
            # Simple query to test connection
            session.execute("SELECT 1")
            
            return {
                "status": "healthy",
                "service": "knowledge_base",
                "database": "connected",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Knowledge base health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "knowledge_base",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        } 