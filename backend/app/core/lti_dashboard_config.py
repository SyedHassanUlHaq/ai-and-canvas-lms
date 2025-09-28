"""
LTI Dashboard Configuration
"""
from pydantic_settings import BaseSettings
from typing import List, Dict, Any, Optional
import os

class LTIDashboardConfig(BaseSettings):
    """LTI Dashboard Configuration Settings"""
    
    # LTI Dashboard Tool Configuration
    lti_dashboard_tool_name: str = "AI Dashboard"
    lti_dashboard_description: str = "AI-powered analytics dashboard for course insights and student performance tracking"
    lti_dashboard_launch_url: str = "/lti_dashboard/launch"
    lti_dashboard_oidc_url: str = "/lti_dashboard/oidc"
    lti_dashboard_config_url: str = "/lti_dashboard/config"
    lti_dashboard_icon_url: str = "/lti_dashboard/icon"
    
    # LTI Dashboard Scopes
    lti_dashboard_scopes: List[str] = [
        "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem",
        "https://purl.imsglobal.org/spec/lti-ags/scope/result",
        "https://purl.imsglobal.org/spec/lti-ags/scope/score",
        "https://purl.imsglobal.org/spec/lti-nrps/scope/contextmembership.readonly"
    ]
    
    # LTI Dashboard Custom Parameters
    lti_dashboard_custom_parameters: Dict[str, str] = {
        "canvas_course_id": "$Canvas.course.id",
        "canvas_user_id": "$Canvas.user.id",
        "canvas_user_name": "$Canvas.user.name",
        "canvas_user_email": "$Canvas.user.email",
        "canvas_course_name": "$Canvas.course.name",
        "canvas_account_id": "$Canvas.account.id"
    }
    
    # LTI Dashboard Message Types
    lti_dashboard_message_types: List[str] = [
        "LtiResourceLinkRequest",
        "LtiDeepLinkingRequest"
    ]
    
    # Platform Storage Configuration
    platform_storage_enabled: bool = True
    platform_storage_target: str = "_parent"
    
    # Canvas API Configuration
    canvas_jwks_url: str = "https://sso.canvaslms.com/api/lti/security/jwks"
    
    # Dashboard specific settings
    dashboard_refresh_interval: int = 300  # 5 minutes
    dashboard_max_metrics: int = 50
    dashboard_max_activities: int = 20
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from environment variables

# Create global instance
lti_dashboard_config = LTIDashboardConfig()
