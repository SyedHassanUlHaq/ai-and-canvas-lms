"""
LTI 1.3 Configuration for AI Tutor Tool
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any
import os
from dotenv import dotenv_values
import pathlib

# Path to .env
env_path = pathlib.Path(__file__).resolve().parent.parent.parent / ".env"
config = dotenv_values(env_path)

class LTISettings(BaseModel):
    # LTI Tool Configuration
    tool_title: str = "AI Tutor Assistant"
    tool_description: str = "AI-powered tutoring assistant that provides contextual help"
    tool_url: str = Field(default=config.get("LTI_TOOL_URL", "https://ai-canvas-lms-73183888096.asia-southeast2.run.app"), description="Base URL for the LTI tool")
    
    # LTI 1.3 Configuration
    client_id: str = Field(default=config.get("LTI_CLIENT_ID", "268550000000000022"), description="LTI Client ID - must match Canvas Developer Key")
    deployment_id: str = Field(default=config.get("LTI_DEPLOYMENT_ID", "1"), description="LTI Deployment ID") 
    issuer: str = Field(default=config.get("LTI_ISSUER", "https://canvas.instructure.com"), description="LTI Platform Issuer")
    
    # Security Configuration
    private_key_path: str = Field(default="keys/private.key", description="Path to private key file")
    public_key_path: str = Field(default="keys/public.key", description="Path to public key file")
    key_set_url: str = Field(default="", description="JWKS URL")
    
    # Canvas-specific Configuration
    canvas_url: str = Field(default=config.get("CANVAS_URL", "https://canvas.instructure.com"), description="Canvas base URL")
    
    # Canvas OIDC Auth endpoints (updated to new sso.canvaslms.com domain)
    oidc_auth_endpoint: str = Field(default=config.get("LTI_OIDC_AUTH_ENDPOINT", "https://sso.canvaslms.com/api/lti/authorize_redirect"), description="Canvas OIDC Auth endpoint")
    canvas_jwks_endpoint: str = Field(default=config.get("LTI_CANVAS_JWKS_ENDPOINT", "https://sso.canvaslms.com/api/lti/security/jwks"), description="Canvas Public JWKs endpoint")
    canvas_token_endpoint: str = Field(default=config.get("LTI_CANVAS_TOKEN_ENDPOINT", "https://sso.canvaslms.com/login/oauth2/token"), description="Canvas Grant Host endpoint")
    
    # Tool Configuration
    icon_url: str = Field(default="", description="Icon URL for the tool")
    target_link_uri: str = Field(default="", description="Target link URI")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Set computed fields
        if not self.key_set_url:
            self.key_set_url = f"{self.tool_url}/.well-known/jwks.json"
        if not self.target_link_uri:
            self.target_link_uri = f"{self.tool_url}/lti/launch"
        if not self.icon_url:
            self.icon_url = f"{self.tool_url}/static/ai-tutor-icon.png"

# Create LTI settings instance
lti_settings = LTISettings()

# LTI Tool Configuration JSON for Canvas Registration
def get_lti_tool_config() -> Dict[str, Any]:
    """Generate LTI tool configuration JSON for Canvas registration"""
    return {
        "title": lti_settings.tool_title,
        "scopes": [
            "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem",
            "https://purl.imsglobal.org/spec/lti-nrps/scope/contextmembership.readonly"
        ],
        "extensions": [
            {
                "domain": lti_settings.tool_url.replace("https://", "").replace("http://", ""),
                "tool_id": "ai_tutor_assistant",
                "platform": "canvas.instructure.com",
                "privacy_level": "public",
                "settings": {
                    "text": lti_settings.tool_title,
                    "placements": [
                        {
                            "text": "AI Tutor",
                            "placement": "editor_button",
                            "message_type": "LtiResourceLinkRequest",
                            "target_link_uri": lti_settings.target_link_uri,
                            "icon_url": lti_settings.icon_url,
                            "selection_width": 800,
                            "selection_height": 600
                        }
                    ]
                }
            }
        ],
        "public_jwk_url": lti_settings.key_set_url,
        "description": lti_settings.tool_description,
        "custom_fields": {},
        "target_link_uri": lti_settings.target_link_uri,
        "oidc_initiation_url": f"{lti_settings.tool_url}/lti/login"
    }

# Print configuration for debugging
print(f"LTI Tool URL: {lti_settings.tool_url}")
print(f"LTI Client ID: {lti_settings.client_id}")
print(f"LTI JWKS URL: {lti_settings.key_set_url}")
