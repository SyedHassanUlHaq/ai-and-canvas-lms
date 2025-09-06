"""
LTI 1.3 Data Models
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

class LTIResourceLink(BaseModel):
    """LTI Resource Link Information"""
    id: str
    title: Optional[str] = None
    description: Optional[str] = None

class LTIContext(BaseModel):
    """LTI Context Information"""
    id: str
    label: Optional[str] = None
    title: Optional[str] = None
    type: Optional[List[str]] = None

class LTIPlatform(BaseModel):
    """LTI Platform Information"""
    guid: str
    name: Optional[str] = None
    contact_email: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    version: Optional[str] = None
    product_family_code: Optional[str] = None

class LTILaunchRequest(BaseModel):
    """LTI 1.3 Launch Request"""
    # Required LTI 1.3 claims
    iss: str = Field(..., description="Platform issuer")
    sub: str = Field(..., description="User subject")
    aud: str = Field(..., description="Tool audience")
    exp: int = Field(..., description="Expiration time")
    iat: int = Field(..., description="Issued at time")
    nonce: str = Field(..., description="Nonce for security")
    
    # LTI 1.3 message type
    message_type: str = Field(..., description="LTI message type")
    
    # LTI 1.3 version
    version: str = Field(..., description="LTI version")
    
    # LTI 1.3 deployment ID
    deployment_id: str = Field(..., description="LTI deployment ID")
    
    # LTI 1.3 target link URI
    target_link_uri: str = Field(..., description="Target link URI")
    
    # LTI 1.3 resource link
    resource_link: Optional[LTIResourceLink] = Field(None, description="Resource link information")
    
    # LTI 1.3 context
    context: Optional[LTIContext] = Field(None, description="Context information")
    
    # LTI 1.3 platform
    tool_platform: Optional[LTIPlatform] = Field(None, description="Platform information")
    
    # LTI 1.3 user information
    name: Optional[str] = Field(None, description="User's full name")
    given_name: Optional[str] = Field(None, description="User's given name")
    family_name: Optional[str] = Field(None, description="User's family name")
    email: Optional[str] = Field(None, description="User's email")
    
    # LTI 1.3 roles
    roles: Optional[List[str]] = Field(None, description="User roles")
    
    # Custom parameters
    custom: Optional[Dict[str, Any]] = None
    
    class Config:
        allow_population_by_field_name = True
        field_mapping = {
            "message_type": "https://purl.imsglobal.org/spec/lti/claim/message_type",
            "version": "https://purl.imsglobal.org/spec/lti/claim/version",
            "deployment_id": "https://purl.imsglobal.org/spec/lti/claim/deployment_id",
            "target_link_uri": "https://purl.imsglobal.org/spec/lti/claim/target_link_uri",
            "resource_link": "https://purl.imsglobal.org/spec/lti/claim/resource_link",
            "context": "https://purl.imsglobal.org/spec/lti/claim/context",
            "tool_platform": "https://purl.imsglobal.org/spec/lti/claim/tool_platform",
            "name": "https://purl.imsglobal.org/spec/lti/claim/name",
            "given_name": "https://purl.imsglobal.org/spec/lti/claim/given_name",
            "family_name": "https://purl.imsglobal.org/spec/lti/claim/family_name",
            "email": "https://purl.imsglobal.org/spec/lti/claim/email",
            "roles": "https://purl.imsglobal.org/spec/lti/claim/roles"
        }

class LTIDeepLinkingRequest(BaseModel):
    """LTI 1.3 Deep Linking Request"""
    # Extends launch request with deep linking specific claims
    deep_linking_settings: Dict[str, Any] = Field(..., description="Deep linking settings")

class LTIToolConfiguration(BaseModel):
    """LTI 1.3 Tool Configuration"""
    title: str
    scopes: List[str]
    extensions: List[Dict[str, Any]]
    custom_fields: Dict[str, str]
    target_link_uri: str
    oidc_initiation_url: str
    public_jwk: Dict[str, Any]

class LTILaunchResponse(BaseModel):
    """LTI 1.3 Launch Response"""
    status: str
    message: str
    user_id: Optional[str] = None
    course_id: Optional[str] = None
    roles: Optional[List[str]] = None
    session_token: Optional[str] = None
    error: Optional[str] = None

class LTIDeepLinkingResponse(BaseModel):
    """LTI 1.3 Deep Linking Response"""
    content_items: List[Dict[str, Any]]
    data: Optional[str] = None
    msg: Optional[str] = None
    log: Optional[str] = None
    errors: Optional[List[str]] = None 