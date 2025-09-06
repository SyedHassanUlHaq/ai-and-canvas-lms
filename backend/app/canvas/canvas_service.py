"""
Canvas LMS API Service - Clean Version
Handles essential communication with Canvas API for iframe widget
"""

import requests
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from app.core.canvas_config import canvas_settings

logger = logging.getLogger(__name__)


class CanvasService:
    """Service for interacting with Canvas LMS API"""
    
    def __init__(self):
        """Initialize Canvas service with configuration"""
        self.base_url = canvas_settings.canvas_url.rstrip('/')
        self.api_token = canvas_settings.canvas_api_token
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        
    def _make_request(self, endpoint: str, method: str = 'GET', data: Dict = None) -> Optional[Dict]:
        """Make HTTP request to Canvas API"""
        logger.info(f"🌐 Canvas API Request: {method} {endpoint}")
        logger.info(f"🔗 Full URL: {self.base_url}/api/v1{endpoint}")
        
        try:
            url = f"{self.base_url}/api/v1{endpoint}"
            
            logger.info(f"📡 Making {method} request to Canvas API...")
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=data)
                logger.info(f"🔍 GET request with params: {data}")
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method == 'PUT':
                response = requests.put(url, headers=self.headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers)
            else:
                logger.error(f"❌ Unsupported HTTP method: {method}")
                return None
            
            logger.info(f"📡 Canvas API Response: {response.status_code} {response.reason}")
            
            if response.status_code == 200:
                logger.info(f"✅ Canvas API request successful")
                response_data = response.json()
                logger.info(f"📊 Response data type: {type(response_data).__name__}")
                if isinstance(response_data, list):
                    logger.info(f"📊 Response contains {len(response_data)} items")
                elif isinstance(response_data, dict):
                    logger.info(f"📊 Response contains {len(response_data)} keys")
                return response_data
            elif response.status_code == 401:
                logger.error("❌ Canvas API authentication failed")
                logger.error(f"📋 Response text: {response.text}")
                return None
            elif response.status_code == 404:
                logger.error(f"❌ Canvas API endpoint not found: {endpoint}")
                logger.error(f"📋 Response text: {response.text}")
                return None
            else:
                logger.error(f"❌ Canvas API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"💥 Error making Canvas API request: {e}")
            logger.error(f"📋 Error type: {type(e).__name__}")
            logger.error(f"📚 Full error info: {e}")
            return None
    
    def get_course_info(self, course_id: str) -> Optional[Dict]:
        """Get course information from Canvas"""
        logger.info(f"📚 get_course_info() called for course ID: {course_id}")
        endpoint = f"/courses/{course_id}"
        result = self._make_request(endpoint)
        if result:
            logger.info(f"✅ Course info retrieved successfully for course {course_id}")
        else:
            logger.warning(f"⚠️ No course info found for course {course_id}")
        return result
    
    def get_all_courses(self) -> Optional[List[Dict]]:
        """Get all courses available to the current user"""
        logger.info("📚 get_all_courses() called")
        
        # Build endpoint with parameters for student-accessible courses
        endpoint = "/courses"
        params = {
            "state[]": ["available", "completed"],  # Only published/active courses for students
            "enrollment_type": "student",  # Only courses where user is enrolled as student
            "per_page": 100  # Get up to 100 courses
        }
        
        result = self._make_request(endpoint, data=params)
        if result:
            logger.info(f"✅ Retrieved {len(result)} courses successfully")
        else:
            logger.warning("⚠️ No courses found")
        return result
    
    def get_course_modules(self, course_id: str) -> Optional[List[Dict]]:
        """Get all modules for a course"""
        logger.info(f"📚 get_course_modules() called for course ID: {course_id}")
        endpoint = f"/courses/{course_id}/modules"
        params = {
            "include[]": ["items", "content_details"],
            "per_page": 100
        }
        
        result = self._make_request(endpoint, data=params)
        if result:
            logger.info(f"✅ Retrieved {len(result)} modules for course {course_id}")
        else:
            logger.warning(f"⚠️ No modules found for course {course_id}")
        return result
    
    def get_page_content(self, course_id: str, page_id: str) -> Optional[Dict]:
        """Get full content for a specific page"""
        logger.info(f"📄 get_page_content() called for course {course_id}, page {page_id}")
        endpoint = f"/courses/{course_id}/pages/{page_id}"
        
        result = self._make_request(endpoint)
        if result:
            logger.info(f"✅ Page content retrieved successfully for page {page_id}")
            # Log content length for debugging
            body_length = len(result.get("body", "")) if result.get("body") else 0
            logger.info(f"📊 Page body length: {body_length} characters")
        else:
            logger.warning(f"⚠️ No page content found for page {page_id}")
        return result
    
    def test_connection(self) -> bool:
        """Test Canvas API connection"""
        try:
            # Try to get account info (lightweight endpoint)
            response = requests.get(f"{self.base_url}/api/v1/accounts", headers=self.headers)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Canvas connection test failed: {e}")
            return False

    def get_module_items(self, course_id: str, module_id: str) -> Optional[List[Dict]]:
        """Get items within a specific module"""
        logger.info(f"📚 get_module_items() called for course {course_id}, module {module_id}")
        endpoint = f"/courses/{course_id}/modules/{module_id}/items"
        params = {
            "per_page": 100
        }
        
        result = self._make_request(endpoint, data=params)
        if result:
            logger.info(f"✅ Retrieved {len(result)} items for module {module_id}")
        else:
            logger.warning(f"⚠️ No items found for module {module_id}")
        return result
    
    def get_course_pages(self, course_id: str) -> Optional[List[Dict]]:
        """Get all pages for a course with full content"""
        logger.info(f"📄 get_course_pages() called for course {course_id}")
        endpoint = f"/courses/{course_id}/pages"
        params = {
            "per_page": 100
        }
        
        # First get page list
        pages_list = self._make_request(endpoint, data=params)
        if not pages_list:
            logger.warning(f"⚠️ No pages found for course {course_id}")
            return None
        
        logger.info(f"📄 Found {len(pages_list)} pages, fetching individual content...")
        
        # Now fetch full content for each page
        full_pages = []
        for page in pages_list:
            page_id = page.get("page_id") or page.get("id")
            if page_id:
                full_page = self.get_page_content(course_id, page_id)
                if full_page:
                    full_pages.append(full_page)
                else:
                    # Fallback to metadata if full content fetch fails
                    full_pages.append(page)
            else:
                full_pages.append(page)
        
        logger.info(f"✅ Retrieved full content for {len(full_pages)} pages")
        return full_pages
    
    def get_course_assignments(self, course_id: str) -> Optional[List[Dict]]:
        """Get all assignments for a course"""
        logger.info(f"📝 get_course_assignments() called for course {course_id}")
        endpoint = f"/courses/{course_id}/assignments"
        params = {
            "per_page": 100
        }
        
        result = self._make_request(endpoint, data=params)
        if result:
            logger.info(f"✅ Retrieved {len(result)} assignments for course {course_id}")
        else:
            logger.warning(f"⚠️ No assignments found for course {course_id}")
        return result

    # Essential CSP Methods
    async def get_csp_settings(self, course_id: str) -> Optional[Dict]:
        """Get Content Security Policy settings for a course"""
        logger.info(f"🛡️ get_csp_settings() called for course ID: {course_id}")
        endpoint = f"/courses/{course_id}/csp_settings"
        result = self._make_request(endpoint)
        if result:
            logger.info(f"✅ CSP settings retrieved successfully for course {course_id}")
        else:
            logger.warning(f"⚠️ No CSP settings found for course {course_id}")
        return result

    async def set_csp_setting(self, course_id: str, status: str) -> Optional[Dict]:
        """Enable, disable, or clear explicit CSP setting for a course"""
        logger.info(f"🔧 set_csp_setting() called for course ID: {course_id}, status: {status}")
        endpoint = f"/courses/{course_id}/csp_settings"
        data = {"status": status}
        result = self._make_request(endpoint, method='PUT', data=data)
        if result:
            logger.info(f"✅ CSP setting updated successfully for course {course_id} to {status}")
        else:
            logger.warning(f"⚠️ Failed to update CSP setting for course {course_id}")
        return result

    async def add_csp_domain(self, course_id: str, domain: str) -> Optional[Dict]:
        """Add an allowed domain to course CSP whitelist"""
        logger.info(f"🌐 add_csp_domain() called for course ID: {course_id}, domain: {domain}")
        endpoint = f"/courses/{course_id}/csp_settings/domains"
        data = {"domain": domain}
        result = self._make_request(endpoint, method='POST', data=data)
        if result:
            logger.info(f"✅ Domain {domain} added to CSP whitelist for course {course_id}")
        else:
            logger.warning(f"⚠️ Failed to add domain {domain} to CSP whitelist for course {course_id}")
        return result

    def get_module_item_sequence(self, course_id: str, asset_type: str, asset_id: str) -> Optional[Dict]:
        """Get module item sequence from Canvas API"""
        logger.info(f"🔍 get_module_item_sequence() called for course {course_id}, asset_type: {asset_type}, asset_id: {asset_id}")
        
        endpoint = f"/courses/{course_id}/module_item_sequence"
        params = {
            "asset_type": asset_type,
            "asset_id": asset_id
        }
        
        result = self._make_request(endpoint, data=params)
        if result:
            logger.info(f"✅ Retrieved module item sequence for course {course_id}")
            logger.info(f"📊 Sequence contains {len(result.get('items', []))} items")
        else:
            logger.warning(f"⚠️ No module item sequence found for course {course_id}")
        
        return result


# Global instance
canvas_service = CanvasService() 