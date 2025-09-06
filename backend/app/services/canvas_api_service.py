"""
Canvas API Service for LTI Integration
Handles Canvas API calls for course modules, user progress, and completion tracking
"""
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class CanvasAPIService:
    """Service for interacting with Canvas APIs via LTI Advantage"""
    
    def __init__(self):
        self.base_url = None
        self.access_token = None
        self.course_id = None
        self.user_id = None
        
    def set_lti_context(self, base_url: str, access_token: str, course_id: str, user_id: str):
        """Set LTI context for Canvas API calls"""
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.course_id = course_id
        self.user_id = user_id
        
        # Validate course_id
        if not course_id or course_id == 'None':
            logger.warning(f"Invalid course_id provided: {course_id}")
            logger.warning("Canvas API calls will fail without a valid course_id")
            logger.warning("Check LTI tool configuration for custom_course_id=$Canvas.course.id")
        
        logger.info(f"Canvas API context set for course: {course_id}, user: {user_id}")
    
    def set_course_id(self, course_id: str):
        """Manually set course ID if not available from LTI context"""
        if course_id and course_id != 'None':
            self.course_id = course_id
            logger.info(f"Course ID manually set to: {course_id}")
        else:
            logger.error(f"Invalid course_id provided: {course_id}")
    
    def _make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated request to Canvas API"""
        if not all([self.base_url, self.access_token, self.course_id]):
            logger.error("Canvas API context not properly set")
            return None
            
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Making Canvas API request: {method} {url}")
        logger.info(f"Headers: {headers}")
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=10)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            logger.info(f"Canvas API response status: {response.status_code}")
            logger.info(f"Canvas API response headers: {dict(response.headers)}")
            
            if response.status_code == 401:
                logger.error("Canvas API authentication failed - token may be invalid")
                return None
            elif response.status_code == 403:
                logger.error("Canvas API access forbidden - insufficient permissions")
                return None
            elif response.status_code == 404:
                logger.error("Canvas API endpoint not found")
                return None
            
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response content: {response.text[:500]}")
                return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Canvas API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Canvas API call: {e}")
            return None
    
    def get_course_modules(self) -> List[Dict[str, Any]]:
        """Get course modules with items and content details"""
        try:
            endpoint = f"/api/v1/courses/{self.course_id}/modules"
            params = {
                "include[]": "items",
                "include[]": "content_details"
            }
            
            # Build query string for parameters
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_endpoint = f"{endpoint}?{query_string}"
            
            logger.info(f"Fetching course modules from Canvas REST API: {full_endpoint}")
            modules_data = self._make_request(full_endpoint)
            
            if modules_data:
                logger.info(f"Modules data received: {len(modules_data)} modules")
                
                # Process modules to add additional metadata
                processed_modules = []
                for module in modules_data:
                    processed_module = self._process_module_data(module)
                    processed_modules.append(processed_module)
                
                logger.info(f"Processed {len(processed_modules)} modules for course {self.course_id}")
                return processed_modules
            else:
                logger.warning("Failed to get modules: No response data")
                return []
                
        except Exception as e:
            logger.error(f"Error getting course modules: {e}")
            return []
    
    def get_module_details(self, module_id: str, student_id: str = None) -> Dict[str, Any]:
        """Get detailed information about a specific module using GET /api/v1/courses/:course_id/modules/:id"""
        try:
            endpoint = f"/api/v1/courses/{self.course_id}/modules/{module_id}"
            params = {
                "include[]": "items",
                "include[]": "content_details"
            }
            
            if student_id:
                params["student_id"] = student_id
            
            # Build query string for parameters
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_endpoint = f"{endpoint}?{query_string}"
            
            logger.info(f"Fetching detailed module information: {full_endpoint}")
            module_data = self._make_request(full_endpoint)
            
            if module_data:
                logger.info(f"Module details received for module {module_id}")
                return self._process_module_data(module_data)
            else:
                logger.warning("Failed to get module details: No response data")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting module details: {e}")
            return {}
    
    def get_module_items(self, module_id: str, student_id: str = None, search_term: str = None) -> List[Dict[str, Any]]:
        """Get detailed list of items in a module using GET /api/v1/courses/:course_id/modules/:module_id/items"""
        try:
            endpoint = f"/api/v1/courses/{self.course_id}/modules/{module_id}/items"
            params = {
                "include[]": "content_details"
            }
            
            if student_id:
                params["student_id"] = student_id
            
            if search_term:
                params["search_term"] = search_term
            
            # Build query string for parameters
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_endpoint = f"{endpoint}?{query_string}"
            
            logger.info(f"Fetching module items: {full_endpoint}")
            items_data = self._make_request(full_endpoint)
            
            if items_data:
                logger.info(f"Module items received: {len(items_data)} items for module {module_id}")
                return items_data
            else:
                logger.warning("Failed to get module items: No response data")
                return []
                
        except Exception as e:
            logger.error(f"Error getting module items: {e}")
            return []
    
    def get_module_item_details(self, module_id: str, item_id: str, student_id: str = None) -> Dict[str, Any]:
        """Get detailed information about a specific module item using GET /api/v1/courses/:course_id/modules/:module_id/items/:id"""
        try:
            endpoint = f"/api/v1/courses/{self.course_id}/modules/{module_id}/items/{item_id}"
            params = {
                "include[]": "content_details"
            }
            
            if student_id:
                params["student_id"] = student_id
            
            # Build query string for parameters
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_endpoint = f"{endpoint}?{query_string}"
            
            logger.info(f"Fetching module item details: {full_endpoint}")
            item_data = self._make_request(full_endpoint)
            
            if item_data:
                logger.info(f"Module item details received for item {item_id}")
                return item_data
            else:
                logger.warning("Failed to get module item details: No response data")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting module item details: {e}")
            return {}
    
    def _process_module_data(self, module: Dict[str, Any]) -> Dict[str, Any]:
        """Process and enhance module data with additional metadata"""
        try:
            processed_module = {
                "id": module.get("id"),
                "name": module.get("name"),
                "position": module.get("position"),
                "state": module.get("state"),
                "published": module.get("published", True),
                "unlock_at": module.get("unlock_at"),
                "require_sequential_progress": module.get("require_sequential_progress", False),
                "prerequisite_module_ids": module.get("prerequisite_module_ids", []),
                "items": []
            }
            
            # Process module items with enhanced details
            if "items" in module:
                for item in module["items"]:
                    item_info = {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "type": item.get("type"),
                        "content_id": item.get("content_id"),
                        "completion_requirement": item.get("completion_requirement"),
                        "published": item.get("published", True),
                        "indent": item.get("indent", 0),
                        "url": item.get("url"),
                        "page_url": item.get("page_url"),
                        "external_url": item.get("external_url"),
                        "new_tab": item.get("new_tab", False),
                        "completion_requirement": item.get("completion_requirement", {})
                    }
                    
                    # Add content details if available
                    if "content_details" in item:
                        content_details = item["content_details"]
                        item_info["content_details"] = {
                            "points_possible": content_details.get("points_possible"),
                            "due_at": content_details.get("due_at"),
                            "unlock_at": content_details.get("unlock_at"),
                            "lock_at": content_details.get("lock_at"),
                            "locked": content_details.get("locked", False),
                            "hidden": content_details.get("hidden", False),
                            "lock_info": content_details.get("lock_info", {}),
                            "lock_explanation": content_details.get("lock_explanation")
                        }
                    
                    processed_module["items"].append(item_info)
            
            return processed_module
            
        except Exception as e:
            logger.error(f"Error processing module data: {e}")
            return module
    
    def get_user_progress(self) -> Dict[str, Any]:
        """Get user's progress through the course using Canvas REST API"""
        # Use the proper Canvas REST API endpoint for user progress
        endpoint = f"/api/v1/courses/{self.course_id}/users/{self.user_id}/progress"
        
        logger.info(f"Fetching user progress from Canvas REST API: {endpoint}")
        progress_data = self._make_request(endpoint)
        
        if not progress_data:
            logger.warning("No progress data returned from Canvas API")
            # Return fallback progress data
            return {
                "completion": 0,
                "total_activity": 0,
                "total_activity_time": 0,
                "last_activity": None,
                "requirement_count": 0,
                "requirement_completed_count": 0,
                "error": "Could not fetch progress from Canvas API"
            }
        
        logger.info(f"Progress data received: {progress_data.keys()}")
        
        return {
            "completion": progress_data.get("completion", 0),
            "total_activity": progress_data.get("total_activity", 0),
            "total_activity_time": progress_data.get("total_activity_time", 0),
            "last_activity": progress_data.get("last_activity"),
            "requirement_count": progress_data.get("requirement_count", 0),
            "requirement_completed_count": progress_data.get("requirement_completed_count", 0),
            "canvas_response": progress_data
        }
    
    def get_module_completion(self, module_id: str) -> Dict[str, Any]:
        """Get completion status for a specific module"""
        endpoint = f"/api/v1/courses/{self.course_id}/modules/{module_id}/items"
        params = "?include[]=completion"
        
        items_data = self._make_request(endpoint + params)
        if not items_data:
            return {}
        
        completion_summary = {
            "module_id": module_id,
            "total_items": len(items_data),
            "completed_items": 0,
            "incomplete_items": 0,
            "items": []
        }
        
        for item in items_data:
            completion = item.get("completion_requirement", {})
            item_status = {
                "id": item.get("id"),
                "title": item.get("title"),
                "type": item.get("type"),
                "completed": completion.get("completed", False),
                "requirement_type": completion.get("type"),
                "min_score": completion.get("min_score"),
                "score": completion.get("score")
            }
            
            if item_status["completed"]:
                completion_summary["completed_items"] += 1
            else:
                completion_summary["incomplete_items"] += 1
            
            completion_summary["items"].append(item_status)
        
        logger.info(f"Module {module_id} completion: {completion_summary['completed_items']}/{completion_summary['total_items']}")
        return completion_summary
    
    def get_current_module_context(self) -> Dict[str, Any]:
        """Get the current module context based on user progress"""
        modules = self.get_course_modules()
        if not modules:
            return {}
        
        # Find the first incomplete module
        current_module = None
        next_module = None
        
        for i, module in enumerate(modules):
            if module["state"] != "completed":
                if current_module is None:
                    current_module = module
                    # Get next module if available
                    if i + 1 < len(modules):
                        next_module = modules[i + 1]
                break
        
        if not current_module:
            # All modules completed
            return {
                "status": "completed",
                "message": "All course modules have been completed!",
                "current_module": modules[-1] if modules else None,
                "next_module": None
            }
        
        # Get completion details for current module
        completion = self.get_module_completion(str(current_module["id"]))
        
        return {
            "status": "in_progress",
            "current_module": current_module,
            "next_module": next_module,
            "completion": completion,
            "progress_percentage": (completion.get("completed_items", 0) / completion.get("total_items", 1)) * 100
        }
    
    def get_recommended_content(self) -> List[Dict[str, Any]]:
        """Get recommended content based on user progress"""
        context = self.get_current_module_context()
        if not context or context.get("status") == "completed":
            return []
        
        current_module = context.get("current_module")
        if not current_module:
            return []
        
        # Get incomplete items from current module
        completion = context.get("completion", {})
        incomplete_items = [
            item for item in completion.get("items", [])
            if not item.get("completed", False)
        ]
        
        # Sort by priority (assignments first, then readings, etc.)
        priority_order = {
            "Assignment": 1,
            "Quiz": 2,
            "Discussion": 3,
            "Page": 4,
            "File": 5,
            "ExternalUrl": 6
        }
        
        incomplete_items.sort(key=lambda x: priority_order.get(x.get("type", ""), 999))
        
        return incomplete_items[:5]  # Return top 5 recommendations
    
    def get_course_analytics(self) -> Dict[str, Any]:
        """Get course analytics for the user"""
        endpoint = f"/api/v1/courses/{self.course_id}/analytics/users/{self.user_id}/assignments"
        
        analytics_data = self._make_request(endpoint)
        if not analytics_data:
            return {}
        
        return {
            "assignments": analytics_data,
            "total_assignments": len(analytics_data),
            "completed_assignments": len([a for a in analytics_data if a.get("submission", {}).get("submitted_at")]),
            "average_score": sum(a.get("score", 0) for a in analytics_data if a.get("score")) / max(len([a for a in analytics_data if a.get("score")]), 1)
        }

# Global instance
canvas_api_service = CanvasAPIService() 