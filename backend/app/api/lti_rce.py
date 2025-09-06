"""
LTI API endpoints for AI Tutor Tool
Handles LTI launch, deep linking, and tool configuration
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os

from app.services.lti_service_rce import lti_service
from app.core.lti_config_rce import get_lti_tool_config

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/lti", tags=["lti"])

# Templates directory
templates_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
templates = Jinja2Templates(directory=templates_dir)

@router.get("/login_rce")
async def lti_login_get(
    request: Request,
    iss: str = None,
    login_hint: str = None,
    target_link_uri: str = None,
    lti_message_hint: str = None
):
    """OIDC login endpoint for LTI 1.3 (GET)"""
    try:
        logger.info(f"🔐 LTI login GET request received")
        logger.info(f"  - Issuer: {iss}")
        logger.info(f"  - Login hint: {login_hint}")
        logger.info(f"  - Target link URI: {target_link_uri}")
        
        # Generate login URL
        login_url = lti_service.generate_login_url(
            login_hint=login_hint or "",
            target_link_uri=target_link_uri or "",
            lti_message_hint=lti_message_hint
        )
        
        # Redirect to Canvas login
        return RedirectResponse(url=login_url)
        
    except Exception as e:
        logger.error(f"❌ Error in LTI login GET: {e}")
        raise HTTPException(status_code=500, detail="LTI login GET failed")

@router.post("/login_rce")
async def lti_login_post(
    request: Request,
    iss: str = Form(None),
    login_hint: str = Form(None),
    target_link_uri: str = Form(None),
    lti_message_hint: str = Form(None)
):
    """OIDC login endpoint for LTI 1.3 (POST)"""
    try:
        logger.info(f"🔐 LTI login POST request received")
        logger.info(f"  - Request method: {request.method}")
        logger.info(f"  - Request URL: {request.url}")
        logger.info(f"  - Request headers: {dict(request.headers)}")
        
        # Try to get parameters from form data first
        if not any([iss, login_hint, target_link_uri, lti_message_hint]):
            # If no form data, try to get from request body
            try:
                body = await request.json()
                logger.info(f"  - Request body (JSON): {body}")
                iss = body.get('iss') or iss
                login_hint = body.get('login_hint') or login_hint
                target_link_uri = body.get('target_link_uri') or target_link_uri
                lti_message_hint = body.get('lti_message_hint') or lti_message_hint
            except:
                # If JSON parsing fails, try to get from query parameters
                params = request.query_params
                logger.info(f"  - Query parameters: {dict(params)}")
                iss = params.get('iss') or iss
                login_hint = params.get('login_hint') or login_hint
                target_link_uri = params.get('target_link_uri') or target_link_uri
                lti_message_hint = params.get('lti_message_hint') or lti_message_hint
        
        logger.info(f"  - Final parameters:")
        logger.info(f"    - Issuer: {iss}")
        logger.info(f"    - Login hint: {login_hint}")
        logger.info(f"    - Target link URI: {target_link_uri}")
        logger.info(f"    - LTI message hint: {lti_message_hint}")
        
        # Generate login URL
        login_url = lti_service.generate_login_url(
            login_hint=login_hint or "",
            target_link_uri=target_link_uri or "",
            lti_message_hint=lti_message_hint
        )
        
        logger.info(f"  - Generated login URL: {login_url}")
        logger.info(f"  - Redirecting to Canvas OIDC endpoint...")
        
        # Redirect to Canvas login
        return RedirectResponse(url=login_url)
        
    except Exception as e:
        logger.error(f"❌ Error in LTI login POST: {e}")
        raise HTTPException(status_code=500, detail="LTI login POST failed")


@router.post("/launch_rce")
async def lti_launch(
    request: Request,
    id_token: str = Form(None),
    state: str = Form(None)
):
    """LTI launch endpoint - receives the ID token from Canvas"""
    try:
        logger.info(f"🚀 LTI launch request received")
        
        # Log all form data to see what Canvas is actually sending
        form_data = await request.form()
        logger.info(f"📝 Form data received:")
        for key, value in form_data.items():
            logger.info(f"  - {key}: {value[:100] if value and len(str(value)) > 100 else value}")
        
        # Check if Canvas returned an OIDC error
        error = form_data.get('error')
        if error:
            error_description = form_data.get('error_description', 'Unknown error')
            logger.error(f"❌ Canvas OIDC error: {error} - {error_description}")
            logger.error(f"❌ State: {form_data.get('state', 'No state')}")
            
            # Return a user-friendly error page
            error_html = f"""
            <html>
            <head><title>LTI Tool Error</title></head>
            <body>
                <h2>LTI Tool Configuration Error</h2>
                <p><strong>Error:</strong> {error}</p>
                <p><strong>Description:</strong> {error_description}</p>
                <p>Please contact your administrator to fix the LTI tool configuration.</p>
                <p><a href="javascript:window.close()">Close</a></p>
            </body>
            </html>
            """
            return HTMLResponse(content=error_html)
        
        # Try to get id_token from different possible parameter names
        id_token_value = id_token
        if not id_token_value:
            # Canvas might send it as 'id_token', 'token', or in the body
            id_token_value = form_data.get('id_token') or form_data.get('token') or form_data.get('id_token')
        
        if not id_token_value:
            # Log the raw body to see what's there
            body = await request.body()
            logger.info(f"📝 Raw request body: {body.decode('utf-8', errors='ignore')[:500]}")
            raise HTTPException(status_code=400, detail="Missing ID token. Received form fields: " + str(list(form_data.keys())))
        
        logger.info(f"✅ Found ID token: {id_token_value[:50]}...")
        
        # Validate ID token
        token_data = lti_service.validate_id_token(id_token_value)
        if not token_data:
            raise HTTPException(status_code=400, detail="Invalid ID token")
        
        logger.info(f"✅ Token validated for user: {token_data.get('sub', 'unknown')}")
        logger.info(f"  - Course context: {token_data.get('https://purl.imsglobal.org/spec/lti/claim/context', {})}")
        logger.info(f"  - Message type: {token_data.get('https://purl.imsglobal.org/spec/lti/claim/message_type', 'unknown')}")
        
        # Extract LTI claims
        context = token_data.get('https://purl.imsglobal.org/spec/lti/claim/context', {})
        custom = token_data.get('https://purl.imsglobal.org/spec/lti/claim/custom', {})
        message_type = token_data.get('https://purl.imsglobal.org/spec/lti/claim/message_type', '')
        
        # Log all available claims to find the return URL
        logger.info(f"🔍 All LTI token claims:")
        for key, value in token_data.items():
            if isinstance(value, str) and len(value) > 100:
                logger.info(f"  - {key}: {value[:100]}...")
            else:
                logger.info(f"  - {key}: {value}")
        
        # Try different possible locations for return URL
        return_url = (
            # Check deep linking settings first (this is where Canvas actually puts it)
            token_data.get('https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings', {}).get('deep_link_return_url') or
            # Fallback locations
            token_data.get('https://purl.imsglobal.org/spec/lti-dl/claim/return_url') or
            token_data.get('return_url') or
            token_data.get('https://purl.imsglobal.org/spec/lti/claim/deep_linking_return_url') or
            token_data.get('deep_linking_return_url')
        )
        
        # If no return URL found, try to construct it from Canvas domain
        if not return_url:
            # Extract Canvas domain from issuer or construct from common patterns
            issuer = token_data.get('iss', '')
            if 'taclegacy.instructure.com' in issuer:
                return_url = 'https://taclegacy.instructure.com/api/lti/return'
            elif 'canvas.instructure.com' in issuer:
                return_url = 'https://canvas.instructure.com/api/lti/return'
            elif 'sso.canvaslms.com' in issuer:
                return_url = 'https://sso.canvaslms.com/api/lti/return'
            else:
                # Try to extract domain from issuer
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(issuer)
                    domain = parsed.netloc
                    return_url = f"https://{domain}/api/lti/return"
                except:
                    pass
        
        logger.info(f"🔗 Deep linking return URL found: {return_url}")
        
        # Store LTI context in session (in production, use proper session management)
        lti_context = {
            'user_id': token_data.get('sub'),
            'course_id': context.get('id'),
            'course_title': context.get('title'),
            'custom': custom,
            'return_url': return_url
        }
        
        print('CONTEXT', lti_context)
        
        # repo = ConversationMemoryRawRepository(db)
        
        # Log the LTI context for debugging
        logger.info(f"🔗 LTI Context created:")
        logger.info(f"  - User ID: {lti_context['user_id']}")
        logger.info(f"  - Course ID: {lti_context['course_id']}")
        logger.info(f"  - Course Title: {lti_context['course_title']}")
        logger.info(f"  - Return URL: {lti_context['return_url']}")
        
        # Handle different message types
        if message_type == 'LtiDeepLinkingRequest':
            logger.info("🔗 Processing Deep Linking Request")
            
            # Create content item for deep linking
            content_item = lti_service.create_content_item(
                type='html',
                title='AI Tutor Assistant',
                text='AI-powered tutoring assistant embedded in your content',
                html=get_ai_tutor_embed_html(lti_context)
            )
            
            # Create deep linking response
            deep_link_response = lti_service.create_deep_linking_response(
                content_items=[content_item],
                data=state
            )
            
            # Return the deep linking response form
            return HTMLResponse(content=create_deep_linking_form(deep_link_response, lti_context.get('return_url')))
            
        elif message_type == 'LtiResourceLinkRequest':
            logger.info("🔗 Processing Resource Link Request")
            # For resource link requests, we could show a different interface
            # For now, redirect to the AI Tutor widget
            return RedirectResponse(url=f"/ai-tutor?course_id={lti_context.get('course_id', 'unknown')}&user_id={lti_context.get('user_id', 'unknown')}")
            
        else:
            logger.warning(f"⚠️ Unknown message type: {message_type}")
            raise HTTPException(status_code=400, detail=f"Unsupported message type: {message_type}")
        
    except Exception as e:
        logger.error(f"❌ Error in LTI launch: {e}")
        raise HTTPException(status_code=500, detail="LTI launch failed")

@router.get("/.well-known/jwks.json")
async def get_jwks():
    """JSON Web Key Set endpoint for LTI tool"""
    try:
        logger.info("🔑 JWKS endpoint accessed")
        jwks = lti_service.get_jwks()
        logger.info(f"🔑 Returning JWKS: {jwks}")
        return jwks
    except Exception as e:
        logger.error(f"❌ Error getting JWKS: {e}")
        raise HTTPException(status_code=500, detail="JWKS generation failed")

# Alternative JWKS endpoint without dot prefix
@router.get("/well-known/jwks.json")
async def get_jwks_alt():
    """Alternative JWKS endpoint for LTI tool"""
    try:
        logger.info("🔑 Alternative JWKS endpoint accessed")
        jwks = lti_service.get_jwks()
        logger.info(f"🔑 Returning JWKS: {jwks}")
        return jwks
    except Exception as e:
        logger.error(f"❌ Error getting JWKS: {e}")
        raise HTTPException(status_code=500, detail="JWKS generation failed")

# Test endpoint to verify routing
@router.get("/test-jwks")
async def test_jwks():
    """Test endpoint to verify JWKS generation"""
    try:
        logger.info("🔑 Test JWKS endpoint accessed")
        jwks = lti_service.get_jwks()
        logger.info(f"🔑 Test JWKS: {jwks}")
        return {"message": "JWKS test successful", "jwks": jwks}
    except Exception as e:
        logger.error(f"❌ Error in test JWKS: {e}")
        return {"error": str(e)}

@router.get("/config_rce")
async def get_lti_config():
    """Get LTI tool configuration for Canvas registration"""
    try:
        config = get_lti_tool_config()
        return config
    except Exception as e:
        logger.error(f"❌ Error getting LTI config: {e}")
        raise HTTPException(status_code=500, detail="LTI config generation failed")

def get_ai_tutor_embed_html(lti_context: Dict[str, Any]) -> str:
    """Generate HTML for embedding AI Tutor widget"""
    
    # Extract context information
    course_id = lti_context.get('course_id', 'unknown')
    course_title = lti_context.get('course_title', 'Unknown Course')
    user_id = lti_context.get('user_id', 'unknown')
    
    # Use absolute URL for iframe (Canvas RCE context)
    tool_url = "https://ai-canvas-lms-73183888096.asia-southeast2.run.app"
    
    # Use static course ID 240 for database access
    database_course_id = "240"
    
    # Create the embedded widget HTML - Canvas-compatible without inline JavaScript
    embed_html = f"""
   
        <div id="ai-tutor-widget-{course_id}" style="min-height: 400px;">
            <iframe 
                src="{tool_url}/ai-tutor?course_id={database_course_id}&user_id={user_id}&course_title={course_title}&lti_launch=true&context_type=lti_embed&database_course_id={database_course_id}"
                style="width: 100%; height: 500px; border: none; border-radius: 8px;"
                title="AI Tutor Assistant"
                allow="microphone; camera"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals">
            </iframe>
        </div>
        
    """
    
    return embed_html

def create_deep_linking_form(deep_link_response: Dict[str, Any], return_url: str = None) -> str:
    """Create HTML form for deep linking response"""
    
    response_token = deep_link_response['response_token']
    
    # If no return URL provided, use a default or show error
    if not return_url:
        return """
        <!DOCTYPE html>
        <html>
        <head><title>LTI Error</title></head>
        <body>
            <h2>❌ LTI Configuration Error</h2>
            <p>Missing return URL for deep linking. Please contact your administrator.</p>
            <p><a href="javascript:window.close()">Close</a></p>
        </body>
        </html>
        """
    
    form_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Tutor - Deep Linking</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 500px;
                margin: 0 auto;
            }}
            .loading {{
                color: #666;
                margin: 20px 0;
            }}
            .spinner {{
                width: 40px;
                height: 40px;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #008ee2;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🎓 AI Tutor Assistant</h2>
            <p>Setting up your AI Tutor widget...</p>
            
            <div class="loading">
                <div class="spinner"></div>
                <p>Embedding AI Tutor into your content...</p>
            </div>
            
            <form id="lti-response-form" method="POST" action="{return_url}">
                <input type="hidden" name="JWT" value="{response_token}">
            </form>
            
            <script>
                // Auto-submit the form to complete deep linking
                setTimeout(function() {{
                    document.getElementById('lti-response-form').submit();
                }}, 2000);
            </script>
        </div>
    </body>
    </html>
    """
    
    return form_html 