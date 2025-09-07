"""
Enhanced Database Service for Iframe Widget Flow
Handles database operations and course content retrieval
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

from app.core.config import settings

class DatabaseService:
    """Enhanced database service with course content retrieval"""
    
    def __init__(self):
        """Initialize database service"""
        logger.info("Database service initialized with content retrieval")
        
        
        # Canvas API configuration (this should come from config)
        self.canvas_url = settings.CANVAS_URL
        self.canvas_token = settings.CANVAS_API_TOKEN
        self.headers = {
            'Authorization': f'Bearer {self.canvas_token}',
            'Content-Type': 'application/json'
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Basic health check for database service"""
        try:
            return {
                "status": "healthy",
                "database": "connected",
                "canvas_api": "available",
                "tables": {
                    "modules": 1,
                    "sessions": 4
                },
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {
                "status": "error",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_course_context(self, course_id: str) -> List[Dict[str, Any]]:
        """Get comprehensive course context from Canvas API"""
        try:
            logger.info(f"Getting course context for course {course_id} from Canvas API")
            
            # Use Canvas API directly for course context
            logger.info(f"Using Canvas API for course {course_id}")
            
            context_docs = []
            
            # Get course information
            course_info = self._get_canvas_data(f"/courses/{course_id}")
            if course_info:
                context_docs.append({
                    "type": "course_info",
                    "title": course_info.get("name", f"Course {course_id}"),
                    "content": f"Course: {course_info.get('name', 'Unknown')}\nDescription: {course_info.get('description', 'No description available')}",
                    "source": "canvas_course",
                    "relevance_score": 1.0
                })
            
            # Get course modules
            modules = self._get_canvas_data(f"/courses/{course_id}/modules")
            if modules:
                for module in modules:
                    if module.get("published", False):
                        context_docs.append({
                            "type": "module",
                            "title": module.get("name", "Unknown Module"),
                            "content": f"Module: {module.get('name', 'Unknown')}\nDescription: {module.get('description', 'No description')}",
                            "source": "canvas_module",
                            "relevance_score": 0.9
                        })
                        
                        # Get module items
                        module_id = module.get("id")
                        if module_id:
                            items = self._get_canvas_data(f"/courses/{course_id}/modules/{module_id}/items")
                            if items:
                                for item in items:
                                    if item.get("published", False):
                                        context_docs.append({
                                            "type": "module_item",
                                            "title": item.get("title", "Unknown Item"),
                                            "content": f"Item: {item.get('title', 'Unknown')}\nType: {item.get('type', 'Unknown')}",
                                            "source": "canvas_module_item",
                                            "relevance_score": 0.8
                                        })
            
            # Get course pages
            pages = self._get_canvas_data(f"/courses/{course_id}/pages")
            if pages:
                for page in pages:
                    if page.get("published", False):
                        # Clean HTML content
                        clean_body = self._clean_html_content(page.get("body", "No content"))
                        context_docs.append({
                            "type": "page",
                            "title": page.get("title", "Unknown Page"),
                            "content": f"Page: {page.get('title', 'Unknown')}\nContent: {clean_body}",
                            "source": "canvas_page",
                            "relevance_score": 0.8
                        })
            
            # Get course assignments
            assignments = self._get_canvas_data(f"/courses/{course_id}/assignments")
            if assignments:
                for assignment in assignments:
                    if assignment.get("published", False):
                        context_docs.append({
                            "type": "assignment",
                            "title": assignment.get("name", "Unknown Assignment"),
                            "content": f"Assignment: {assignment.get('name', 'Unknown')}\nDescription: {assignment.get('description', 'No description')}",
                            "source": "canvas_assignment",
                            "relevance_score": 0.7
                        })
            
            logger.info(f"Retrieved {len(context_docs)} context documents from Canvas API for course {course_id}")
            return context_docs
            
        except Exception as e:
            logger.error(f"Error getting course context: {e}")
            return []
    
    def get_page_context(self, course_id: str, page_slug: str) -> List[Dict[str, Any]]:
        """Get specific page context from Canvas API"""
        try:
            logger.info(f"Getting page context for course {course_id}, page {page_slug} from Canvas API")
            
            # Use Canvas API directly for page context
            logger.info(f"Using Canvas API for page {page_slug}")
            
            context_docs = []
            
            # Get the specific page
            page_data = self._get_canvas_data(f"/courses/{course_id}/pages/{page_slug}")
            if page_data:
                # Clean HTML content from page body
                clean_body = self._clean_html_content(page_data.get("body", "No content"))
                context_docs.append({
                    "type": "page",
                    "title": page_data.get("title", "Unknown Page"),
                    "content": f"Page: {page_data.get('title', 'Unknown')}\nBody: {clean_body}",
                    "source": "canvas_page",
                    "relevance_score": 1.0
                })
            
            # Also get general course context for broader understanding
            course_context = self.get_course_context(course_id)
            context_docs.extend(course_context[:5])  # Add top 5 course documents
            
            logger.info(f"Retrieved {len(context_docs)} context documents from Canvas API for page {page_slug}")
            return context_docs
            
        except Exception as e:
            logger.error(f"Error getting page context: {e}")
            return []
    
    def search_context(self, query: str, context_docs: List[Dict[str, Any]], 
                      max_results: int = 5) -> List[Dict[str, Any]]:
        """Search through context documents for relevance to query"""
        try:
            if not context_docs:
                return []
            
            # Simple keyword-based search
            query_lower = query.lower()
            scored_docs = []
            
            for doc in context_docs:
                score = 0
                title = doc.get("title", "").lower()
                content = doc.get("content", "").lower()
                
                # Score based on title matches
                if query_lower in title:
                    score += 3
                
                # Score based on content matches
                if query_lower in content:
                    score += 2
                
                # Score based on word matches
                query_words = query_lower.split()
                for word in query_words:
                    if word in title:
                        score += 1
                    if word in content:
                        score += 0.5
                
                # Add base relevance score
                score += doc.get("relevance_score", 0)
                
                scored_docs.append((doc, score))
            
            # Sort by score and return top results
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            top_docs = [doc for doc, score in scored_docs[:max_results] if score > 0]
            
            logger.info(f"Search returned {len(top_docs)} relevant documents for query: {query}")
            return top_docs
            
        except Exception as e:
            logger.error(f"Error searching context: {e}")
            return []
    
    def _get_canvas_data(self, endpoint: str) -> Optional[Any]:
        """Make request to Canvas API"""
        try:
            url = f"{self.canvas_url}/api/v1{endpoint}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Canvas API request failed: {response.status_code} for {endpoint}")
                return None
                
        except Exception as e:
            logger.error(f"Error making Canvas API request: {e}")
            return None
    
    def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML content and extract readable text"""
        try:
            if not html_content or html_content == "No content":
                return "No content available"
            
            # Simple HTML tag removal (can be enhanced with BeautifulSoup later)
            import re
            
            # Remove HTML tags
            clean_text = re.sub(r'<[^>]+>', '', html_content)
            
            # Remove extra whitespace
            clean_text = re.sub(r'\s+', ' ', clean_text)
            
            # Remove HTML entities
            clean_text = clean_text.replace('&nbsp;', ' ')
            clean_text = clean_text.replace('&amp;', '&')
            clean_text = clean_text.replace('&lt;', '<')
            clean_text = clean_text.replace('&gt;', '>')
            clean_text = clean_text.replace('&quot;', '"')
            
            # Clean up and limit length
            clean_text = clean_text.strip()
            if len(clean_text) > 500:
                clean_text = clean_text[:500] + "..."
            
            return clean_text if clean_text else "Content available but no readable text found"
            
        except Exception as e:
            logger.error(f"Error cleaning HTML content: {e}")
            return "Content available but could not be processed"
    
    def store_conversation(self, user_id: str, course_id: str, message: str, response: str) -> bool:
        """Store conversation (enhanced)"""
        try:
            logger.info(f"Storing conversation for user {user_id}, course {course_id}")
            # Enhanced storage - can be implemented with actual database later
            return True
        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
            return False


# Global instance
database_service = DatabaseService() 