"""
LTI 1.3 Service
Handles LTI 1.3 authentication, launch, and deep linking
"""
import jwt
import logging
import time
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import requests

from app.core.lti_config import lti_config
from app.models.lti_models import (
    LTILaunchRequest, LTIDeepLinkingRequest, 
    LTILaunchResponse, LTIDeepLinkingResponse,
    LTIToolConfiguration
)

logger = logging.getLogger(__name__)

class LTIService:
    """LTI 1.3 Service for handling LTI operations"""
    
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.kid = None
        self._load_or_generate_keys()
    
    def _load_or_generate_keys(self):
        """Load existing keys or generate new ones"""
        try:
            # Try to load existing keys
            self._load_keys()
        except FileNotFoundError:
            # Generate new keys if they don't exist
            self._generate_keys()
            self._save_keys()
    
    def _generate_keys(self):
        """Generate RSA key pair for LTI 1.3"""
        try:
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # Get public key
            public_key = private_key.public_key()
            
            # Convert to PEM format
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            self.private_key = private_pem.decode('utf-8')
            self.public_key = public_pem.decode('utf-8')
            self.kid = str(uuid.uuid4())
            
            logger.info("Generated new LTI 1.3 RSA key pair")
            
        except Exception as e:
            logger.error(f"Error generating LTI keys: {e}")
            raise
    
    def _save_keys(self):
        """Save keys to files"""
        try:
            with open(lti_config.lti_private_key_path, 'w') as f:
                f.write(self.private_key)
            
            with open(lti_config.lti_public_key_path, 'w') as f:
                f.write(self.public_key)
                
            logger.info("LTI keys saved to files")
            
        except Exception as e:
            logger.error(f"Error saving LTI keys: {e}")
            raise
    
    def _load_keys(self):
        """Load existing keys from files"""
        try:
            with open(lti_config.lti_private_key_path, 'r') as f:
                self.private_key = f.read()
            
            with open(lti_config.lti_public_key_path, 'r') as f:
                self.public_key = f.read()
            
            # Extract kid from public key or generate new one
            self.kid = str(uuid.uuid4())
            
            logger.info("LTI keys loaded from files")
            
        except Exception as e:
            logger.error(f"Error loading LTI keys: {e}")
            raise
    
    def get_public_jwk(self) -> Dict[str, Any]:
        """Get public JWK for LTI 1.3 tool configuration"""
        try:
            # Parse public key to get components
            from cryptography.hazmat.primitives.serialization import load_pem_public_key
            pub_key = load_pem_public_key(self.public_key.encode(), backend=default_backend())
            
            # Extract key components
            numbers = pub_key.public_numbers()
            
            jwk = {
                "kty": "RSA",
                "kid": self.kid,
                "use": "sig",
                "alg": "RS256",
                "n": self._int_to_base64url(numbers.n),
                "e": self._int_to_base64url(numbers.e)
            }
            
            return jwk
            
        except Exception as e:
            logger.error(f"Error generating JWK: {e}")
            raise
    
    def _int_to_base64url(self, value: int) -> str:
        """Convert integer to base64url encoding"""
        import base64
        
        # Convert to bytes
        byte_length = (value.bit_length() + 7) // 8
        value_bytes = value.to_bytes(byte_length, byteorder='big')
        
        # Encode to base64 and convert to base64url
        base64_str = base64.b64encode(value_bytes).decode('utf-8')
        return base64_str.rstrip('=').replace('+', '-').replace('/', '_')
    
    def verify_lti_request(self, id_token: str, client_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Verify LTI 1.3 ID token"""
        try:
            # Decode token without verification first to get issuer
            unverified_payload = jwt.decode(id_token, options={"verify_signature": False})
            issuer = unverified_payload.get('iss')
            
            if not issuer:
                logger.error("No issuer found in LTI token")
                return False, None
            
            # Get platform's public keys
            platform_keys = self._get_platform_keys(issuer)
            if not platform_keys:
                logger.error(f"Could not retrieve platform keys for issuer: {issuer}")
                return False, None
            
            # Verify token with platform's public key
            for key in platform_keys:
                try:
                    payload = jwt.decode(
                        id_token,
                        key,
                        algorithms=['RS256'],
                        audience=client_id,
                        options={
                            'verify_exp': True,
                            'verify_iat': True,
                            'require': ['exp', 'iat', 'iss', 'sub', 'aud']
                        }
                    )
                    
                    # Additional LTI 1.3 specific validations
                    if not self._validate_lti_claims(payload):
                        continue
                    
                    logger.info(f"LTI token verified successfully for user: {payload.get('sub')}")
                    return True, payload
                    
                except jwt.InvalidTokenError:
                    continue
            
            logger.error("LTI token verification failed with all platform keys")
            return False, None
            
        except Exception as e:
            logger.error(f"Error verifying LTI token: {e}")
            return False, None
    
    def _get_platform_keys(self, issuer: str) -> List[str]:
        """Get platform's public keys from Canvas JWKS endpoint"""
        try:
            # Use the new Canvas JWKS endpoint
            from app.core.lti_config import lti_config
            
            # For Canvas, use the new sso.canvaslms.com endpoint
            if "canvas.instructure.com" in issuer or "sso.canvaslms.com" in issuer:
                jwks_url = lti_config.canvas_jwks_url
            else:
                # Fallback to OIDC discovery for other platforms
                discovery_url = f"{issuer}/.well-known/openid_configuration"
                response = requests.get(discovery_url, timeout=10)
                response.raise_for_status()
                discovery_data = response.json()
                jwks_url = discovery_data.get('jwks_uri')
                
                if not jwks_url:
                    logger.error("No JWKS URI found in OIDC discovery")
                    return []
            
            # Get JWKS
            jwks_response = requests.get(jwks_url, timeout=10)
            jwks_response.raise_for_status()
            
            jwks_data = jwks_response.json()
            keys = jwks_data.get('keys', [])
            
            # Convert JWK to PEM format
            public_keys = []
            for key in keys:
                try:
                    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
                    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
                    
                    # Convert base64url to integers
                    n = self._base64url_to_int(key['n'])
                    e = self._base64url_to_int(key['e'])
                    
                    # Create public key
                    numbers = RSAPublicNumbers(e, n)
                    public_key = numbers.public_key(backend=default_backend())
                    
                    # Convert to PEM
                    pem = public_key.public_bytes(
                        encoding=Encoding.PEM,
                        format=PublicFormat.SubjectPublicKeyInfo
                    )
                    
                    public_keys.append(pem.decode('utf-8'))
                    
                except Exception as e:
                    logger.warning(f"Error converting JWK to PEM: {e}")
                    continue
            
            return public_keys
            
        except Exception as e:
            logger.error(f"Error getting platform keys: {e}")
            return []
    
    def _base64url_to_int(self, value: str) -> int:
        """Convert base64url string to integer"""
        import base64
        
        # Convert base64url to base64
        base64_str = value.replace('-', '+').replace('_', '/')
        padding = 4 - (len(base64_str) % 4)
        if padding != 4:
            base64_str += '=' * padding
        
        # Decode to bytes and convert to integer
        value_bytes = base64.b64decode(base64_str)
        return int.from_bytes(value_bytes, byteorder='big')
    
    def _validate_lti_claims(self, payload: Dict[str, Any]) -> bool:
        """Validate LTI 1.3 specific claims"""
        try:
            # Check required LTI claims
            required_claims = [
                'https://purl.imsglobal.org/spec/lti/claim/message_type',
                'https://purl.imsglobal.org/spec/lti/claim/version',
                'https://purl.imsglobal.org/spec/lti/claim/deployment_id'
            ]
            
            for claim in required_claims:
                if claim not in payload:
                    logger.error(f"Missing required LTI claim: {claim}")
                    return False
            
            # Validate message type
            message_type = payload.get('https://purl.imsglobal.org/spec/lti/claim/message_type')
            if message_type not in lti_config.lti_message_types:
                logger.error(f"Invalid LTI message type: {message_type}")
                return False
            
            # Validate version
            version = payload.get('https://purl.imsglobal.org/spec/lti/claim/version')
            if version != '1.3.0':
                logger.error(f"Invalid LTI version: {version}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating LTI claims: {e}")
            return False
    
    def create_lti_session(self, lti_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create LTI session data from verified payload"""
        try:
            # Debug: Log the full LTI payload structure
            logger.info(f"Creating LTI session from payload with keys: {list(lti_payload.keys())}")
            logger.info(f"LTI payload context: {lti_payload.get('context')}")
            logger.info(f"LTI payload custom fields: {lti_payload.get('custom')}")
            
            session_data = {
                "user_id": lti_payload.get('sub'),
                "course_id": None,
                "user_name": None,
                "user_email": None,
                "user_roles": [],
                "lti_context_id": None,
                "lti_resource_link_id": None,
                "lti_deployment_id": lti_payload.get('deployment_id'),
                "lti_platform_guid": None,
                "session_token": str(uuid.uuid4()),
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                # Platform Storage support
                "platform_storage_enabled": True,
                "platform_storage_target": "_parent"  # Will change to "post_message_forwarding" after Aug 19, 2023
            }
            
            # Extract user information
            if 'name' in lti_payload:
                session_data["user_name"] = lti_payload['name']
            
            if 'email' in lti_payload:
                session_data["user_email"] = lti_payload['email']
            
            # Extract roles
            if 'roles' in lti_payload:
                session_data["user_roles"] = lti_payload['roles']
            
            # For specific course implementation, use hardcoded course ID
            from app.core.lti_config import lti_config
            if lti_config.use_real_canvas_api:
                session_data["course_id"] = lti_config.specific_course_id
                session_data["use_real_canvas_api"] = True
                logger.info(f"Using hardcoded course ID: {lti_config.specific_course_id}")
                logger.info("Real Canvas API integration enabled for this course")
            else:
                # Extract context information - handle both full claim URLs and simplified field names
                context_key = None
                if 'https://purl.imsglobal.org/spec/lti/claim/context' in lti_payload:
                    context_key = 'https://purl.imsglobal.org/spec/lti/claim/context'
                elif 'context' in lti_payload:
                    context_key = 'context'
                    
                if context_key and lti_payload[context_key]:
                    context = lti_payload[context_key]
                    session_data["lti_context_id"] = context.get('id')
                    session_data["course_id"] = context.get('id')  # Use context ID as course ID
                    logger.info(f"Extracted course_id from {context_key}: {context.get('id')}")
            
            # Extract resource link information - handle both full claim URLs and simplified field names
            resource_link_key = None
            if 'https://purl.imsglobal.org/spec/lti/claim/resource_link' in lti_payload:
                resource_link_key = 'https://purl.imsglobal.org/spec/lti/claim/resource_link'
            elif 'resource_link' in lti_payload:
                resource_link_key = 'resource_link'
                
            if resource_link_key and lti_payload[resource_link_key]:
                resource_link = lti_payload[resource_link_key]
                session_data["lti_resource_link_id"] = resource_link.get('id')
            
            # Extract platform information - handle both full claim URLs and simplified field names
            platform_key = None
            if 'https://purl.imsglobal.org/spec/lti/claim/tool_platform' in lti_payload:
                platform_key = 'https://purl.imsglobal.org/spec/lti/claim/tool_platform'
            elif 'tool_platform' in lti_payload:
                platform_key = 'tool_platform'
                
            if platform_key and lti_payload[platform_key]:
                platform = lti_payload[platform_key]
                session_data["lti_platform_guid"] = platform.get('guid')
            
            # Try alternative course ID extraction methods
            if not session_data["course_id"]:
                # Try custom fields with Canvas variable substitutions - handle both full claim URLs and simplified field names
                custom_key = None
                if 'https://purl.imsglobal.org/spec/lti/claim/custom' in lti_payload:
                    custom_key = 'https://purl.imsglobal.org/spec/lti/claim/custom'
                elif 'custom' in lti_payload:
                    custom_key = 'custom'
                    
                if custom_key and lti_payload[custom_key]:
                    custom = lti_payload[custom_key]
                    logger.info(f"Custom fields available from {custom_key}: {list(custom.keys())}")
                    
                    # Canvas variable substitutions (in order of preference)
                    if 'canvas_course_id' in custom and custom['canvas_course_id'] != '$Canvas.course.id':
                        session_data["course_id"] = custom['canvas_course_id']
                        logger.info(f"Extracted course_id from custom.canvas_course_id: {custom['canvas_course_id']}")
                    elif 'context_id' in custom and custom['context_id'] != '$Context.id':
                        session_data["course_id"] = custom['context_id']
                        logger.info(f"Extracted course_id from custom.context_id: {custom['context_id']}")
                    elif 'course_id' in custom:
                        session_data["course_id"] = custom['course_id']
                        logger.info(f"Extracted course_id from custom.course_id: {custom['course_id']}")
                    
                    # Log all custom field values for debugging
                    for key, value in custom.items():
                        if 'course' in key.lower() or 'context' in key.lower():
                            logger.info(f"Custom field {key}: {value}")
                
                # Try direct fields
                if 'course_id' in lti_payload:
                    session_data["course_id"] = lti_payload['course_id']
                    logger.info(f"Extracted course_id from direct field: {lti_payload['course_id']}")
                
                # Try context_id field (LTI standard) - handle both full claim URLs and simplified field names
                context_id_keys = [k for k in lti_payload.keys() if 'context_id' in k.lower()]
                for key in context_id_keys:
                    if lti_payload[key]:
                        session_data["course_id"] = lti_payload[key]
                        logger.info(f"Extracted course_id from {key}: {lti_payload[key]}")
                        break
                
                # Try launch_presentation_context_id - handle both full claim URLs and simplified field names
                launch_presentation_key = None
                if 'https://purl.imsglobal.org/spec/lti/claim/launch_presentation' in lti_payload:
                    launch_presentation_key = 'https://purl.imsglobal.org/spec/lti/claim/launch_presentation'
                elif 'launch_presentation' in lti_payload:
                    launch_presentation_key = 'launch_presentation'
                    
                if launch_presentation_key and lti_payload[launch_presentation_key]:
                    presentation = lti_payload[launch_presentation_key]
                    if 'context_id' in presentation:
                        session_data["course_id"] = presentation['context_id']
                        logger.info(f"Extracted course_id from {launch_presentation_key}.context_id: {presentation['context_id']}")
            
            # If still no course_id, try to extract from context.id (LTI 1.3 standard)
            if not session_data["course_id"] and context_key and lti_payload[context_key]:
                context = lti_payload[context_key]
                if isinstance(context, dict) and 'id' in context:
                    session_data["course_id"] = context['id']
                    logger.info(f"Extracted course_id from {context_key}.id: {context['id']}")
                elif isinstance(context, str):
                    session_data["course_id"] = context
                    logger.info(f"Extracted course_id from {context_key} string: {context}")
            
            # Try standard LTI fields that should always be present
            if not session_data["course_id"]:
                # Check for context_id in various locations
                context_id_keys = [k for k in lti_payload.keys() if 'context_id' in k.lower()]
                for key in context_id_keys:
                    if lti_payload[key]:
                        session_data["course_id"] = lti_payload[key]
                        logger.info(f"Extracted course_id from {key}: {lti_payload[key]}")
                        break
                
                # Check resource_link for context_id
                if resource_link_key and lti_payload[resource_link_key]:
                    resource_link = lti_payload[resource_link_key]
                    if isinstance(resource_link, dict) and 'context_id' in resource_link:
                        session_data["course_id"] = resource_link['context_id']
                        logger.info(f"Extracted course_id from {resource_link_key}.context_id: {resource_link['context_id']}")
            
            logger.info(f"Final course_id: {session_data['course_id']}")
            
            # If course_id is still None, log a warning but don't fail
            if not session_data["course_id"]:
                logger.warning("Could not extract course_id from LTI payload - Canvas API calls may fail")
                logger.warning("Canvas variable substitutions configured: custom_canvas_course_id=$Canvas.course.id, custom_context_id=$Context.id")
                logger.warning("Check if Canvas is properly substituting these variables")
                
                # Log the full payload structure for debugging
                logger.warning(f"Available LTI payload keys: {list(lti_payload.keys())}")
                
                # Check for custom fields in both formats
                custom_key = None
                if 'https://purl.imsglobal.org/spec/lti/claim/custom' in lti_payload:
                    custom_key = 'https://purl.imsglobal.org/spec/lti/claim/custom'
                elif 'custom' in lti_payload:
                    custom_key = 'custom'
                    
                if custom_key and lti_payload[custom_key]:
                    logger.warning(f"Custom fields received from {custom_key}: {lti_payload[custom_key]}")
                else:
                    logger.warning("No custom fields found in LTI payload")
                
                # Check for context in both formats
                context_key = None
                if 'https://purl.imsglobal.org/spec/lti/claim/context' in lti_payload:
                    context_key = 'https://purl.imsglobal.org/spec/lti/claim/context'
                elif 'context' in lti_payload:
                    context_key = 'context'
                    
                if context_key and lti_payload[context_key]:
                    logger.warning(f"Context data received from {context_key}: {lti_payload[context_key]}")
                else:
                    logger.warning("No context data found in LTI payload")
            
            logger.info(f"Created LTI session for user: {session_data['user_id']}")
            return session_data
            
        except Exception as e:
            logger.error(f"Error creating LTI session: {e}")
            raise
    
    def get_platform_storage_target(self) -> str:
        """Get the current platform storage target frame"""
        from app.core.lti_config import lti_config
        return lti_config.platform_storage_target
    
    def is_platform_storage_enabled(self) -> bool:
        """Check if platform storage is enabled"""
        from app.core.lti_config import lti_config
        return lti_config.platform_storage_enabled
    
    def generate_nonce(self) -> str:
        """Generate a nonce for OIDC authentication"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def get_tool_configuration(self, base_url: str) -> LTIToolConfiguration:
        """Get LTI 1.3 tool configuration"""
        try:
            config = LTIToolConfiguration(
                title=lti_config.lti_tool_name,
                scopes=lti_config.lti_scopes,
                extensions=[
                    {
                        "platform": "canvas.instructure.com",
                        "settings": {
                            "platform": "canvas.instructure.com",
                            "placements": [
                                {
                                    "placement": "course_navigation",
                                    "enabled": True,
                                    "text": "AI Tutor",
                                    "message_type": "LtiResourceLinkRequest",
                                    "target_link_uri": f"{base_url}{lti_config.lti_launch_url}",
                                    "icon_url": f"{base_url}/lti/icon",
                                    "canvas_icon_class": "icon-lti",
                                    "display_type": "full_width",
                                    "visibility": "public"
                                },
                                {
                                    "placement": "assignment_selection",
                                    "enabled": True,
                                    "text": "AI Tutor",
                                    "message_type": "LtiResourceLinkRequest",
                                    "target_link_uri": f"{base_url}{lti_config.lti_launch_url}",
                                    "icon_url": f"{base_url}/lti/icon",
                                    "canvas_icon_class": "icon-lti",
                                    "display_type": "default",
                                    "visibility": "public"
                                },
                                {
                                    "placement": "link_selection",
                                    "enabled": True,
                                    "text": "AI Tutor",
                                    "message_type": "LtiResourceLinkRequest",
                                    "target_link_uri": f"{base_url}{lti_config.lti_launch_url}",
                                    "icon_url": f"{base_url}/lti/icon",
                                    "canvas_icon_class": "icon-lti",
                                    "display_type": "default",
                                    "visibility": "public"
                                }
                            ]
                        }
                    }
                ],
                custom_fields=lti_config.lti_custom_parameters,
                target_link_uri=f"{base_url}{lti_config.lti_launch_url}",
                oidc_initiation_url=f"{base_url}/lti/oidc",
                public_jwk=self.get_public_jwk()
            )
            
            return config
            
        except Exception as e:
            logger.error(f"Error getting tool configuration: {e}")
            raise

# Create global instance
lti_service = LTIService() 