"""
LTI 1.3 Configuration
"""
from pydantic_settings import BaseSettings
from typing import Dict, Any
import os

class LTIConfig(BaseSettings):
    """LTI 1.3 Configuration Settings"""
    
    # LTI 1.3 Tool Configuration
    lti_tool_name: str = "AI Tutor"
    lti_tool_description: str = "AI-powered tutoring and assessment tool"
    lti_tool_url: str = os.getenv("LTI_TOOL_URL", "https://ai-tutor-xxxxx-xx.a.run.app")
    
    # LTI 1.3 Keys and Secrets
    lti_private_key_path: str = os.getenv("LTI_PRIVATE_KEY_PATH", "private.key")
    lti_public_key_path: str = os.getenv("LTI_PUBLIC_KEY_PATH", "public.key")
    
    # LTI 1.3 Scopes
    lti_scopes: list = [
        "https://purl.imsglobal.org/spec/lti-ags/scope/score",
        "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem",
        "https://purl.imsglobal.org/spec/lti-nrps/scope/contextmembership.readonly"
    ]
    
    # LTI 1.3 Message Types
    lti_message_types: list = [
        "LtiResourceLinkRequest",
        "LtiDeepLinkingRequest"
    ]
    
    # LTI 1.3 Launch URLs
    lti_launch_url: str = "/lti/launch"
    lti_deep_linking_url: str = "/lti/deep-linking"
    lti_tool_config_url: str = "/lti/config"
    
    # LTI 1.3 Canvas Endpoints (Updated for new sso.canvaslms.com domain)
    canvas_oidc_auth_url: str = "https://sso.canvaslms.com/api/lti/authorize_redirect"
    canvas_jwks_url: str = "https://sso.canvaslms.com/api/lti/security/jwks"
    canvas_token_url: str = "https://sso.canvaslms.com/login/oauth2/token"
    
    # LTI 1.3 Platform Storage Support
    platform_storage_enabled: bool = True
    platform_storage_target: str = "_parent"  # Will change to "post_message_forwarding" after Aug 19, 2023
    
    # Specific Course Configuration
    specific_course_id: str = "240"  # Hardcoded course ID for immediate functionality
    use_real_canvas_api: bool = True  # Enable real Canvas API calls for specific course
    
    # LTI 1.3 Custom Parameters
    lti_custom_parameters: Dict[str, str] = {
        "ai_tutor_enabled": "true",
        "quiz_enabled": "true",
        "conversation_enabled": "true",
        # Canvas Variable Substitutions for Course ID
        "canvas_course_id": "$Canvas.course.id",
        "context_id": "$Context.id",
        "canvas_api_domain": "$Canvas.api.domain",
        "canvas_user_id": "$Canvas.user.id",
        "course_title": "$Context.title"
    }
    
    # LTI 1.3 Privacy Settings
    lti_privacy_level: str = "public"  # public, anonymous, name_only
    
    class Config:
        env_prefix = "LTI_"

# Create global instance
lti_config = LTIConfig() 