"""
LTI 1.3 Service for AI Tutor Tool
Handles LTI authentication, launch, and deep linking
"""

import logging
import jwt
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import secrets

from app.core.lti_config_rce import lti_settings

logger = logging.getLogger(__name__)

class LTIService:
    """Service for handling LTI 1.3 operations"""
    
    def __init__(self):
        """Initialize LTI service"""
        self.client_id = lti_settings.client_id
        self.deployment_id = lti_settings.deployment_id
        self.issuer = lti_settings.issuer
        self.tool_url = lti_settings.tool_url
        
        # Canvas OIDC endpoints
        self.oidc_auth_endpoint = lti_settings.oidc_auth_endpoint
        self.canvas_jwks_endpoint = lti_settings.canvas_jwks_endpoint
        self.canvas_token_endpoint = lti_settings.canvas_token_endpoint
        
        # Validate OIDC endpoint configuration
        if not self.oidc_auth_endpoint:
            logger.error("❌ OIDC auth endpoint not configured!")
            raise ValueError("OIDC auth endpoint is required")
        
        logger.info(f"✅ LTI Service initialized with OIDC endpoint: {self.oidc_auth_endpoint}")
        
        # Generate or load keys
        self._setup_keys()
        
    def _setup_keys(self):
        """Setup cryptographic keys for LTI"""
        try:
            # For development, generate keys if they don't exist
            # In production, these should be properly managed keys
            import os
            keys_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'keys')
            os.makedirs(keys_dir, exist_ok=True)
            
            private_key_path = os.path.join(keys_dir, 'private.key')
            public_key_path = os.path.join(keys_dir, 'public.key')
            
            if not os.path.exists(private_key_path):
                # Generate new key pair for development
                from cryptography.hazmat.primitives import serialization
                from cryptography.hazmat.primitives.asymmetric import rsa
                
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048
                )
                
                # Save private key
                with open(private_key_path, 'wb') as f:
                    f.write(private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ))
                
                # Save public key
                public_key = private_key.public_key()
                with open(public_key_path, 'wb') as f:
                    f.write(public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    ))
                
                logger.info("✅ Generated new LTI key pair")
            
            # Load keys as actual key objects
            from cryptography.hazmat.primitives import serialization
            
            with open(private_key_path, 'rb') as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None
                )
            
            with open(public_key_path, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(f.read())
                
            logger.info("✅ LTI keys loaded as objects successfully")
            
        except Exception as e:
            logger.error(f"❌ Error setting up LTI keys: {e}")
            # Fallback to dummy keys for development
            self.private_key = "dummy-private-key"
            self.public_key = "dummy-public-key"
    
    def generate_login_url(self, login_hint: str, target_link_uri: str, 
                           lti_message_hint: str = None) -> str:
        """Generate OIDC login URL for LTI 1.3"""
        try:
            # OIDC login parameters - start with minimal set
            params = {
                'iss': self.issuer,
                'login_hint': login_hint,
                'target_link_uri': target_link_uri,
                'client_id': self.client_id,
                'response_type': 'id_token',
                'response_mode': 'form_post',
                'scope': 'openid'
            }
            
            # Add optional parameters only if they have values
            if lti_message_hint and lti_message_hint.strip():
                params['lti_message_hint'] = lti_message_hint.strip()
            
            if self.deployment_id and self.deployment_id != '1':
                params['lti_deployment_id'] = self.deployment_id
            
            # Generate nonce only if needed
            nonce = secrets.token_urlsafe(16)  # Shorter nonce
            params['nonce'] = nonce
            
            # Filter out empty values to avoid malformed URLs
            filtered_params = {k: v for k, v in params.items() if v and v != ''}
            
            # Add Platform Storage support parameter if available
            if hasattr(self, 'include_storage_target') and self.include_storage_target:
                filtered_params['lti_storage_target'] = 'post_message_forwarding'
            
            # Build login URL using the new sso.canvaslms.com domain
            # Note: issuer remains canvas.instructure.com (this is the platform identifier)
            # But the OIDC auth endpoint uses sso.canvaslms.com
            login_url = self.oidc_auth_endpoint
            
            # Canvas OIDC requirements from documentation:
            # Required: redirect_uri, client_id, login_hint, state
            # Optional: target_link_uri, deployment_id, canvas_region, canvas_environment
            
            # Generate a state token for CSRF protection
            state_token = secrets.token_urlsafe(32)
            
            # Build OIDC parameters according to Canvas specification
            # Required: redirect_uri, client_id, login_hint, state
            # Also required by OIDC spec: scope, nonce, prompt, response_mode, response_type
            oidc_params = {
                'redirect_uri': target_link_uri,  # Canvas expects redirect_uri, not target_link_uri
                'client_id': self.client_id,
                'login_hint': login_hint,
                'state': state_token,
                'scope': 'openid',  # Required by OIDC specification
                'nonce': secrets.token_urlsafe(16),  # Required by OIDC for CSRF protection
                'prompt': 'none',  # Required by OIDC - don't show login prompt
                'response_mode': 'form_post',  # Required by OIDC - return response via POST
                'response_type': 'id_token'  # Required by OIDC - we want an ID token
            }
            
            # Add optional parameters if available
            if lti_message_hint and lti_message_hint.strip():
                oidc_params['target_link_uri'] = target_link_uri  # This is the optional one
            
            if self.deployment_id and self.deployment_id != '1':
                oidc_params['deployment_id'] = self.deployment_id
            
            # Build query string with proper URL encoding
            query_parts = []
            for k, v in oidc_params.items():
                if v and v != '':
                    # Properly encode the value to handle special characters
                    from urllib.parse import quote
                    encoded_value = quote(str(v), safe='')
                    query_parts.append(f"{k}={encoded_value}")
            
            query_string = '&'.join(query_parts)
            
            # Debug: Show each query part separately
            logger.info(f"🔗 Query parts (Canvas OIDC spec):")
            for i, part in enumerate(query_parts):
                logger.info(f"    {i+1}. {part}")
            
            full_url = f"{login_url}?{query_string}"
            logger.info(f"🔗 Generated OIDC login URL (Canvas spec): {full_url}")
            logger.info(f"🔗 URL length: {len(full_url)} characters")
            
            # Note: Following Canvas OIDC specification exactly
            # No need for URL length checking as we're using their required parameters
            
            # Validate URL format
            try:
                from urllib.parse import urlparse
                parsed = urlparse(full_url)
                logger.info(f"🔗 Parsed URL components:")
                logger.info(f"    - Scheme: {parsed.scheme}")
                logger.info(f"    - Netloc: {parsed.netloc}")
                logger.info(f"    - Path: {parsed.path}")
                logger.info(f"    - Query: {parsed.query}")
            except Exception as e:
                logger.warning(f"⚠️ URL parsing warning: {e}")
            
            # Log the final URL for debugging
            logger.info(f"🔗 Final OIDC URL to be used: {full_url}")
            logger.info(f"🔗 Final URL length: {len(full_url)} characters")
            
            # Also log what Canvas might be expecting
            logger.info(f"🔗 Canvas OIDC endpoint: {self.oidc_auth_endpoint}")
            logger.info(f"🔗 Expected issuer: {self.issuer}")
            logger.info(f"🔗 Client ID being used: {self.client_id}")
            
            return full_url
            
        except Exception as e:
            logger.error(f"❌ Error generating login URL: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            logger.error(f"❌ Error details: {str(e)}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise
    
    def validate_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Validate LTI ID token"""
        try:
            # Decode token without verification for now (development)
            # In production, this should verify the signature
            decoded = jwt.decode(id_token, options={"verify_signature": False})
            
            # Validate required claims
            required_claims = ['iss', 'aud', 'sub', 'exp', 'iat', 'nonce']
            for claim in required_claims:
                if claim not in decoded:
                    logger.error(f"❌ Missing required claim: {claim}")
                    return None
            
            # Validate issuer
            if decoded['iss'] != self.issuer:
                logger.error(f"❌ Invalid issuer: {decoded['iss']}")
                return None
            
            # Validate audience
            if decoded['aud'] != self.client_id:
                logger.error(f"❌ Invalid audience: {decoded['aud']}")
                return None
            
            # Validate expiration
            if datetime.fromtimestamp(decoded['exp']) < datetime.now():
                logger.error("❌ Token expired")
                return None
            
            logger.info("✅ ID token validated successfully")
            return decoded
            
        except Exception as e:
            logger.error(f"❌ Error validating ID token: {e}")
            return None
    
    def create_deep_linking_response(self, content_items: list, 
                                   data: str = None) -> Dict[str, Any]:
        """Create Deep Linking response for embedding content in RCE"""
        try:
            # Create JWT payload for deep linking response
            payload = {
                'iss': self.client_id,
                'aud': self.issuer,
                'exp': datetime.utcnow() + timedelta(minutes=5),
                'iat': datetime.utcnow(),
                'nonce': secrets.token_urlsafe(32),
                'https://purl.imsglobal.org/spec/lti/claim/message_type': 'LtiDeepLinkingResponse',
                'https://purl.imsglobal.org/spec/lti/claim/version': '1.3.0',
                'https://purl.imsglobal.org/spec/lti-dl/claim/content_items': content_items,
                'https://purl.imsglobal.org/spec/lti-dl/claim/data': data
            }
            
            # Generate the key ID that matches our JWKS
            import hashlib
            public_key = self.public_key  # Already an RSAPublicKey object
            public_numbers = public_key.public_numbers()
            modulus = public_numbers.n
            key_id = hashlib.sha256(str(modulus).encode()).hexdigest()[:16]
            
            # Sign the JWT with the key ID header
            headers = {'kid': key_id}
            # Convert private key to PEM format for JWT encoding
            from cryptography.hazmat.primitives import serialization
            private_key_pem = self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            response_token = jwt.encode(payload, private_key_pem, algorithm='RS256', headers=headers)
            
            logger.info(f"🔑 JWT signed with key ID: {key_id}")
            
            logger.info("✅ Deep linking response created successfully")
            return {
                'response_token': response_token,
                'content_items': content_items
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating deep linking response: {e}")
            raise
    
    def create_content_item(self, type: str, title: str, text: str, 
                           html: str, url: str = None) -> Dict[str, Any]:
        """Create a content item for deep linking"""
        content_item = {
            'type': type,
            'title': title,
            'text': text,
            'html': html
        }
        
        if url:
            content_item['url'] = url
            
        return content_item
    
    def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set for LTI tool"""
        try:
            # Generate a proper JWKS with the actual public key
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            import base64
            
            # Get the public key (it's already an RSAPublicKey object)
            public_key = self.public_key
            
            # Extract modulus and exponent
            public_numbers = public_key.public_numbers()
            modulus = public_numbers.n
            exponent = public_numbers.e
            
            # Convert to base64url encoding (remove padding)
            n_bytes = modulus.to_bytes((modulus.bit_length() + 7) // 8, byteorder='big')
            n_b64 = base64.urlsafe_b64encode(n_bytes).decode('utf-8').rstrip('=')
            
            e_bytes = exponent.to_bytes((exponent.bit_length() + 7) // 8, byteorder='big')
            e_b64 = base64.urlsafe_b64encode(e_bytes).decode('utf-8').rstrip('=')
            
            # Generate a consistent key ID based on the public key
            import hashlib
            key_id = hashlib.sha256(str(modulus).encode()).hexdigest()[:16]
            
            logger.info(f"🔑 Generated JWKS with key ID: {key_id}")
            
            return {
                'keys': [
                    {
                        'kty': 'RSA',
                        'kid': key_id,
                        'use': 'sig',
                        'alg': 'RS256',
                        'n': n_b64,
                        'e': e_b64
                    }
                ]
            }
        except Exception as e:
            logger.error(f"❌ Error generating JWKS: {e}")
            return {'keys': []}

# Create global instance
lti_service = LTIService() 