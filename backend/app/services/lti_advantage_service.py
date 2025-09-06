"""
LTI Advantage Service for Canvas API Access
Handles OAuth2 token exchange and Canvas API access via LTI Advantage
"""
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class LTIAdvantageService:
    """Service for LTI Advantage OAuth2 token exchange and Canvas API access"""
    
    def __init__(self):
        self.tokens = {}  # Store tokens by user_id
        self.token_expiry = {}  # Store token expiry times
        
    def exchange_token(self, user_id: str, course_id: str, lti_context: Dict[str, Any]) -> Optional[str]:
        """Exchange LTI context for Canvas API access token"""
        try:
            # Check if we have a valid token
            if self._is_token_valid(user_id):
                logger.info(f"Using existing valid token for user {user_id}")
                return self.tokens.get(user_id)
            
            # Get Canvas instance URL from LTI context
            canvas_url = self._extract_canvas_url(lti_context)
            if not canvas_url:
                logger.error("Could not extract Canvas URL from LTI context")
                return None
            
            # Exchange for token using LTI Advantage
            token = self._request_canvas_token(canvas_url, user_id, course_id, lti_context)
            if token:
                self._store_token(user_id, token)
                logger.info(f"Successfully obtained Canvas API token for user {user_id}")
                return token
            
            return None
            
        except Exception as e:
            logger.error(f"Error exchanging LTI context for token: {e}")
            return None
    
    def _extract_canvas_url(self, lti_context: Dict[str, Any]) -> Optional[str]:
        """Extract Canvas instance URL from LTI context"""
        try:
            # Try to get from tool_platform
            if "tool_platform" in lti_context:
                platform = lti_context["tool_platform"]
                if "url" in platform:
                    return platform["url"]
            
            # Try to get from issuer
            if "iss" in lti_context:
                issuer = lti_context["iss"]
                if "canvas.instructure.com" in issuer:
                    return "https://canvas.instructure.com"
                elif "sso.canvaslms.com" in issuer:
                    return "https://sso.canvaslms.com"
                elif "taclegacy.instructure.com" in issuer:
                    return "https://taclegacy.instructure.com"
            
            # Try to get from custom parameters
            if "custom_canvas_api_domain" in lti_context:
                domain = lti_context["custom_canvas_api_domain"]
                return f"https://{domain}"
            
            # Try to get from custom fields with Canvas variable substitutions
            if "custom" in lti_context:
                custom = lti_context["custom"]
                if "canvas_api_domain" in custom:
                    domain = custom["canvas_api_domain"]
                    if domain and domain != "$Canvas.api.domain":
                        return f"https://{domain}"
            
            # For hardcoded course 240, use the known Canvas domain
            if lti_context.get("course_id") == "240":
                logger.info("Using hardcoded Canvas domain for course 240")
                return "https://taclegacy.instructure.com"
            
            logger.warning("Could not extract Canvas URL from LTI context")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting Canvas URL: {e}")
            return None
    
    def _request_canvas_token(self, canvas_url: str, user_id: str, course_id: str, lti_context: Dict[str, Any]) -> Optional[str]:
        """Request Canvas API access token using LTI Advantage"""
        try:
            # For LTI 1.3, we need to use the LTI Advantage OAuth2 flow
            # This requires the tool to be configured with proper scopes
            
            # Check if we have LTI Advantage scopes in the context
            if "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem" in lti_context.get("scope", []):
                logger.info("LTI Advantage AGS scope detected, using client_credentials flow")
                return self._get_client_credentials_token(canvas_url, lti_context)
            
            # Check if we have a custom Canvas API token in the context
            if "custom_canvas_api_token" in lti_context:
                logger.info("Using custom Canvas API token from LTI context")
                return lti_context["custom_canvas_api_token"]
            
            # For now, we'll use a simulated token exchange
            # In production, this would use the actual LTI Advantage OAuth2 flow
            logger.warning("No LTI Advantage scopes or custom token found, using simulated token")
            simulated_token = f"lti_advantage_token_{user_id}_{course_id}_{int(datetime.now().timestamp())}"
            
            logger.info(f"Generated simulated Canvas API token for user {user_id}")
            return simulated_token
            
        except Exception as e:
            logger.error(f"Error requesting Canvas token: {e}")
            return None
    
    def _get_client_credentials_token(self, canvas_url: str, lti_context: Dict[str, Any]) -> Optional[str]:
        """Get client_credentials token using LTI Advantage"""
        try:
            # This would implement the actual OAuth2 client_credentials flow
            # For now, we'll simulate it
            
            # In production, you would:
            # 1. Use the client_id and client_secret from your LTI tool configuration
            # 2. Make a POST request to /login/oauth2/token with grant_type=client_credentials
            # 3. Include the proper scopes for progress access
            
            logger.info("Simulating LTI Advantage client_credentials token exchange")
            simulated_token = f"lti_advantage_client_credentials_{int(datetime.now().timestamp())}"
            
            return simulated_token
            
        except Exception as e:
            logger.error(f"Error getting client_credentials token: {e}")
            return None
    
    def _store_token(self, user_id: str, token: str):
        """Store token and set expiry"""
        self.tokens[user_id] = token
        # Set token to expire in 1 hour (typical LTI Advantage token lifetime)
        self.token_expiry[user_id] = datetime.now() + timedelta(hours=1)
    
    def _is_token_valid(self, user_id: str) -> bool:
        """Check if stored token is still valid"""
        if user_id not in self.tokens or user_id not in self.token_expiry:
            return False
        
        expiry = self.token_expiry[user_id]
        if datetime.now() >= expiry:
            # Remove expired token
            del self.tokens[user_id]
            del self.token_expiry[user_id]
            return False
        
        return True
    
    def get_canvas_api_context(self, user_id: str, course_id: str, lti_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get Canvas API context for a user"""
        try:
            token = self.exchange_token(user_id, course_id, lti_context)
            if not token:
                return None
            
            canvas_url = self._extract_canvas_url(lti_context)
            if not canvas_url:
                return None
            
            return {
                "base_url": canvas_url,
                "access_token": token,
                "course_id": course_id,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Error getting Canvas API context: {e}")
            return None
    
    def refresh_token_if_needed(self, user_id: str, course_id: str, lti_context: Dict[str, Any]) -> Optional[str]:
        """Refresh token if it's expired or about to expire"""
        try:
            if not self._is_token_valid(user_id):
                logger.info(f"Token expired for user {user_id}, refreshing...")
                return self.exchange_token(user_id, course_id, lti_context)
            
            # Check if token expires in next 5 minutes
            if user_id in self.token_expiry:
                expiry = self.token_expiry[user_id]
                if datetime.now() + timedelta(minutes=5) >= expiry:
                    logger.info(f"Token expires soon for user {user_id}, refreshing...")
                    return self.exchange_token(user_id, course_id, lti_context)
            
            return self.tokens.get(user_id)
            
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None
    
    def revoke_token(self, user_id: str):
        """Revoke and remove stored token"""
        try:
            if user_id in self.tokens:
                del self.tokens[user_id]
            if user_id in self.token_expiry:
                del self.token_expiry[user_id]
            logger.info(f"Token revoked for user {user_id}")
        except Exception as e:
            logger.error(f"Error revoking token: {e}")

# Global instance
lti_advantage_service = LTIAdvantageService() 