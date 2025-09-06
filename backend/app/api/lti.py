"""
LTI 1.3 API Endpoints
"""
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.services.lti_service import lti_service
from app.models.lti_models import LTILaunchResponse, LTIDeepLinkingResponse
# from app.services.ai_service import ai_service
from app.services.memory_service import memory_service
# from app.services.lti_ai_service import lti_ai_service
from app.services.canvas_api_service import canvas_api_service
# from app.api.chat import search_similar_chunks
from app.services.vector import AITutor, TutorConfig
from app.repository.conversation_memory import ConversationMemoryRepository, ConversationMemoryRawRepository
from fastapi import Depends
from app.core.dependancies import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.repository.user_sessions import SessionRepository

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/lti", tags=["LTI 1.3"])

# Templates for LTI responses
templates = Jinja2Templates(directory="app/widgets")

@router.get("/config")
async def get_lti_config(request: Request):
    """Get LTI 1.3 tool configuration"""
    try:
        base_url = str(request.base_url).rstrip('/')
        config = lti_service.get_tool_configuration(base_url)
        
        return JSONResponse(content=config.dict())
        
    except Exception as e:
        logger.error(f"Error getting LTI config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get LTI configuration")

@router.get("/oidc")
async def oidc_initiation_get(
    request: Request,
    iss: str = Query(..., description="Platform issuer"),
    login_hint: str = Query(..., description="Login hint"),
    target_link_uri: str = Query(..., description="Target link URI"),
    client_id: str = Query(..., description="Client ID"),
    lti_message_hint: Optional[str] = Query(None, description="LTI message hint")
):
    """OIDC initiation endpoint for LTI 1.3 (GET method)"""
    try:
        logger.info(f"OIDC initiation GET for platform: {iss}, client: {client_id}")
        logger.info(f"Target link URI: {target_link_uri}")
        logger.info(f"Login hint: {login_hint}")
        logger.info(f"LTI message hint: {lti_message_hint}")
        
        # Generate state and nonce for security
        state = lti_service.generate_nonce()
        nonce = lti_service.generate_nonce()
        
        # Store OIDC state for validation (in production, use Redis/database)
        # For now, we'll store in memory service
        oidc_state = {
            "state": state,
            "nonce": nonce,
            "target_link_uri": target_link_uri,
            "client_id": client_id,
            "iss": iss,
            "login_hint": login_hint,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store state for later validation
        memory_service.store_lti_storage(f"oidc_state_{state}", json.dumps(oidc_state))
        
        # Build OIDC authorization request to Canvas
        canvas_oidc_url = "https://sso.canvaslms.com/api/lti/authorize_redirect"
        
        # For LTI 1.3, the redirect_uri should be our launch endpoint
        # Canvas will send the id_token directly to our launch endpoint
        # Force HTTPS for redirect URI (Canvas requires HTTPS)
        base_url = str(request.base_url).rstrip('/')
        if base_url.startswith('http://'):
            base_url = base_url.replace('http://', 'https://')
        our_redirect_uri = base_url + "/lti/launch"
        
        auth_params = {
            "scope": "openid",
            "response_type": "id_token",
            "client_id": client_id,
            "redirect_uri": our_redirect_uri,  # Canvas sends response here
            "login_hint": login_hint,
            "state": state,  # Our generated state for validation
            "response_mode": "form_post",
            "nonce": nonce,
            "prompt": "none"  # Required by Canvas OIDC
        }
        
        # Add issuer if provided
        if iss:
            auth_params["iss"] = iss
        
        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in auth_params.items() if v])
        redirect_url = f"{canvas_oidc_url}?{query_string}"
        
        logger.info(f"Redirecting to Canvas OIDC: {redirect_url}")
        logger.info(f"Our redirect URI: {our_redirect_uri}")
        logger.info(f"Generated state: {state}")
        
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"Error in OIDC initiation GET: {e}")
        raise HTTPException(status_code=500, detail="OIDC initiation failed")

@router.post("/oidc")
async def oidc_initiation_post(
    request: Request,
    iss: str = Form(..., description="Platform issuer"),
    login_hint: str = Form(..., description="Login hint"),
    target_link_uri: str = Form(..., description="Target link URI"),
    client_id: str = Form(..., description="Client ID"),
    lti_message_hint: Optional[str] = Form(None, description="LTI message hint")
):
    """OIDC initiation endpoint for LTI 1.3 (POST method)"""
    try:
        logger.info(f"OIDC initiation POST for platform: {iss}, client: {client_id}")
        logger.info(f"Target link URI: {target_link_uri}")
        logger.info(f"Login hint: {login_hint}")
        logger.info(f"LTI message hint: {lti_message_hint}")
        
        # Generate state and nonce for security
        state = lti_service.generate_nonce()
        nonce = lti_service.generate_nonce()
        
        # Store OIDC state for validation (in production, use Redis/database)
        # For now, we'll store in memory service
        oidc_state = {
            "state": state,
            "nonce": nonce,
            "target_link_uri": target_link_uri,
            "client_id": client_id,
            "iss": iss,
            "login_hint": login_hint,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store state for later validation
        memory_service.store_lti_storage(f"oidc_state_{state}", json.dumps(oidc_state))
        
        # Build OIDC authorization request to Canvas
        canvas_oidc_url = "https://sso.canvaslms.com/api/lti/authorize_redirect"
        
        # For LTI 1.3, the redirect_uri should be our launch endpoint
        # Canvas will send the id_token directly to our launch endpoint
        # Force HTTPS for redirect URI (Canvas requires HTTPS)
        base_url = str(request.base_url).rstrip('/')
        if base_url.startswith('http://'):
            base_url = base_url.replace('http://', 'https://')
        our_redirect_uri = base_url + "/lti/launch"
        
        auth_params = {
            "scope": "openid",
            "response_type": "id_token",
            "client_id": client_id,
            "redirect_uri": our_redirect_uri,  # Canvas sends response here
            "login_hint": login_hint,
            "state": state,  # Our generated state for validation
            "response_mode": "form_post",
            "nonce": nonce,
            "prompt": "none"  # Required by Canvas OIDC
        }
        
        # Add issuer if provided
        if iss:
            auth_params["iss"] = iss
        
        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in auth_params.items() if v])
        redirect_url = f"{canvas_oidc_url}?{query_string}"
        
        logger.info(f"Redirecting to Canvas OIDC: {redirect_url}")
        logger.info(f"Our redirect URI: {our_redirect_uri}")
        logger.info(f"Generated state: {state}")
        
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"Error in OIDC initiation POST: {e}")
        raise HTTPException(status_code=500, detail="OIDC initiation failed")

@router.post("/oidc/callback")
async def oidc_callback(
    request: Request,
    id_token: str = Form(..., description="ID token from Canvas"),
    state: str = Form(..., description="State parameter for validation"),
    client_id: str = Form(..., description="Client ID")
):
    """OIDC callback endpoint that receives the id_token from Canvas"""
    try:
        logger.info(f"OIDC callback received for client: {client_id}")
        logger.info(f"State parameter: {state}")
        logger.info(f"ID token length: {len(id_token) if id_token else 0}")
        
        # Retrieve stored OIDC state for validation
        stored_state_key = f"oidc_state_{state}"
        stored_state_data = memory_service.get_lti_storage(stored_state_key)
        
        if not stored_state_data:
            logger.error(f"No stored OIDC state found for state: {state}")
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        try:
            oidc_state = json.loads(stored_state_data)
        except json.JSONDecodeError:
            logger.error(f"Invalid stored OIDC state data: {stored_state_data}")
            raise HTTPException(status_code=400, detail="Invalid stored state data")
        
        # Validate state
        if oidc_state.get("state") != state:
            logger.error(f"State mismatch: stored={oidc_state.get('state')}, received={state}")
            raise HTTPException(status_code=400, detail="State parameter mismatch")
        
        # Check if state is expired (5 minutes)
        state_timestamp = datetime.fromisoformat(oidc_state.get("timestamp", ""))
        if datetime.now() - state_timestamp > timedelta(minutes=5):
            logger.error(f"OIDC state expired: {state_timestamp}")
            raise HTTPException(status_code=400, detail="State parameter expired")
        
        # Verify the id_token
        is_valid, lti_payload = lti_service.verify_lti_request(id_token, client_id)
        
        if not is_valid:
            logger.error("ID token verification failed in OIDC callback")
            raise HTTPException(status_code=401, detail="Invalid ID token")
        
        # Validate nonce if present in payload
        if "nonce" in lti_payload and oidc_state.get("nonce") != lti_payload.get("nonce"):
            logger.error(f"Nonce mismatch: stored={oidc_state.get('nonce')}, payload={lti_payload.get('nonce')}")
            raise HTTPException(status_code=400, detail="Nonce parameter mismatch")
        
        # Clean up stored state
        memory_service.delete_lti_storage(stored_state_key)
        
        # Create LTI session
        session_data = lti_service.create_lti_session(lti_payload)
        
        # Store session in memory service
        memory_service.store_lti_session(session_data["session_token"], session_data)
        
        # Get the target link URI from stored state
        target_link_uri = oidc_state.get("target_link_uri")
        if not target_link_uri:
            logger.error("No target link URI found in stored state")
            raise HTTPException(status_code=400, detail="Missing target link URI")
        
        # Add session token to target link URI
        if "?" in target_link_uri:
            redirect_url = f"{target_link_uri}&session_token={session_data['session_token']}"
        else:
            redirect_url = f"{target_link_uri}?session_token={session_data['session_token']}"
        
        logger.info(f"OIDC callback successful, redirecting to: {redirect_url}")
        
        # Redirect to the target link URI with session token
        return RedirectResponse(url=redirect_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in OIDC callback: {e}")
        raise HTTPException(status_code=500, detail="OIDC callback failed")

@router.post("/launch")
async def lti_launch(
    request: Request,
    id_token: Optional[str] = Form(None, description="LTI ID token"),
    client_id: Optional[str] = Form(None, description="Client ID"),
    state: Optional[str] = Form(None, description="State parameter from OIDC"),
    lti_storage_target: Optional[str] = Form(None, description="Platform storage target frame"),
    db: AsyncSession = Depends(get_db)
):
    """LTI 1.3 launch endpoint with Platform Storage support and OIDC handling"""
    try:
        # Log the entire request for debugging
        logger.info(f"LTI launch request received")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        
        # Check if this is an OIDC response (has state parameter)
        if state:
            logger.info(f"OIDC response detected with state: {state}")
            
            # Retrieve stored OIDC state for validation
            stored_state_key = f"oidc_state_{state}"
            stored_state_data = memory_service.get_lti_storage(stored_state_key)
            
            if not stored_state_data:
                logger.error(f"No stored OIDC state found for state: {state}")
                raise HTTPException(status_code=400, detail="Invalid state parameter")
            
            try:
                oidc_state = json.loads(stored_state_data)
            except json.JSONDecodeError:
                logger.error(f"Invalid stored OIDC state data: {stored_state_data}")
                raise HTTPException(status_code=400, detail="Invalid stored state data")
            
            # Validate state
            if oidc_state.get("state") != state:
                logger.error(f"State mismatch: stored={oidc_state.get('state')}, received={state}")
                raise HTTPException(status_code=400, detail="State parameter mismatch")
            
            # Check if state is expired (5 minutes)
            state_timestamp = datetime.fromisoformat(oidc_state.get("timestamp", ""))
            if datetime.now() - state_timestamp > timedelta(minutes=5):
                logger.error(f"OIDC state expired: {state_timestamp}")
                raise HTTPException(status_code=400, detail="State parameter expired")
            
            # Check for OIDC errors in form data
            try:
                form_data = await request.form()
                error = form_data.get("error")
                error_description = form_data.get("error_description")
                
                if error:
                    logger.error(f"OIDC error received: {error} - {error_description}")
                    # Clean up stored state
                    memory_service.delete_lti_storage(stored_state_key)
                    raise HTTPException(
                        status_code=400, 
                        detail=f"OIDC authentication failed: {error_description or error}"
                    )
            except Exception as form_error:
                logger.warning(f"Could not check for OIDC errors: {form_error}")
            
            # Clean up stored state
            memory_service.delete_lti_storage(stored_state_key)
            
            # Use stored client_id from OIDC state
            client_id = oidc_state.get("client_id")
            logger.info(f"Using client_id from OIDC state: {client_id}")
        
        # Try to get parameters from form data first
        if not id_token or not client_id:
            # Try to get from query parameters as fallback
            query_params = dict(request.query_params)
            logger.info(f"Query parameters: {query_params}")
            
            # Also try to get from form data with different field names
            try:
                form_data = await request.form()
                logger.info(f"Form data: {dict(form_data)}")
                
                # Check for alternative field names
                id_token = id_token or form_data.get("id_token") or form_data.get("idToken") or form_data.get("token")
                client_id = client_id or form_data.get("client_id") or form_data.get("clientId") or form_data.get("client")
                
            except Exception as form_error:
                logger.warning(f"Could not parse form data: {form_error}")
        
        # If still no id_token or client_id, try to get from request body
        if not id_token or not client_id:
            try:
                body = await request.body()
                logger.info(f"Request body: {body.decode()}")
                
                # Try to parse as JSON
                try:
                    json_data = await request.json()
                    logger.info(f"JSON data: {json_data}")
                    id_token = id_token or json_data.get("id_token") or json_data.get("idToken") or json_data.get("token")
                    client_id = client_id or json_data.get("client_id") or json_data.get("clientId") or json_data.get("client")
                except:
                    pass
                    
            except Exception as body_error:
                logger.warning(f"Could not read request body: {body_error}")
        
        # Final check for required parameters
        if not id_token:
            logger.error("Missing id_token in LTI launch request")
            raise HTTPException(status_code=400, detail="Missing id_token parameter")
        
        if not client_id:
            logger.error("Missing client_id in LTI launch request")
            raise HTTPException(status_code=400, detail="Missing client_id parameter")
        
        logger.info(f"LTI launch request for client: {client_id}")
        logger.info(f"ID token length: {len(id_token) if id_token else 0}")
        
        # Verify LTI token
        is_valid, lti_payload = lti_service.verify_lti_request(id_token, client_id)
        
        if not is_valid:
            logger.error("LTI token verification failed")
            raise HTTPException(status_code=400, detail="Invalid LTI token")
        
        # Create LTI session
        session_data = lti_service.create_lti_session(lti_payload)
        
        # Update platform storage target if provided
        if lti_storage_target:
            session_data["platform_storage_target"] = lti_storage_target
            logger.info(f"Platform storage target: {lti_storage_target}")
        
        # Store session in memory service (you might want to use a proper session store)
        memory_service.store_lti_session(session_data["session_token"], session_data)
        
        # Debug: Verify session was stored
        stored_session = memory_service.get_lti_session(session_data["session_token"])
        logger.info(f"Session stored successfully: {stored_session is not None}")
        logger.info(f"Session token: {session_data['session_token']}")
        logger.info(f"Session data keys: {list(session_data.keys())}")



        # db = SessionLocal()
        repo = ConversationMemoryRawRepository(db)
        repo2 = SessionRepository(db)

        rec = await repo2.create_session(session_data["user_id"], session_data["session_token"])
        logger.info("New Session created for user: ", session_data["user_id"], "with Session ID: ", session_data["session_token"])
        
        # Get user context for AI service
        user_context = {
            "user_id": session_data["user_id"],
            "course_id": session_data["course_id"],
            "user_name": session_data["user_name"],
            "user_roles": session_data["user_roles"]
        }



        was_created, memory = await repo.ensure_user_exists_with_welcome_message(
            user_context=user_context,
            message_from="system"  # You can change this to "user" or "assistant"
        )

        if was_created:
            logger.info("✅ New user created!")
            logger.info(f"   User ID: {memory['user_id']}")
            logger.info(f"   Generated Message: {memory['message']}")
            logger.info(f"   Message Length: {len(memory['message'])} characters")
            logger.info(f"   Session ID: {memory['session_id']}")
            # logger.info(f"   Stored in context: {json.loads(memory.context_used) if memory.context_used else {}}")
        else:
            logger.info("ℹ️  User already exists")
            logger.info(f"   User ID: {memory['user_id']}")
            logger.info(f"   Most recent message: {memory['message']}")
            logger.info(f"   Last activity: {memory['timestamp']}")
            
            
        context = await repo.format_conversations_for_chatbot(memory['session_id'])
  


        print('user context: ', user_context)

        print('context', context)
        
        # Determine which template to use based on LTI placement
        # For course navigation, use the course-specific widget
        template_name = "lti_course_widget.html"
        # db.close()
        # Render LTI launch page
        return templates.TemplateResponse(
            template_name,
            {
                "request": request,
                "lti_session": session_data,
                "user_context": user_context,
                "is_lti": True,
                "platform_storage_target": session_data.get("platform_storage_target", "_parent"),
                'context': context
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in LTI launch: {e}")
        raise HTTPException(status_code=500, detail="LTI launch failed")

@router.post("/chat/refresh")
async def chat_refresh(
    request: Request,
    message: str = Form(..., description="User message"),
    session_token: str = Form(..., description="LTI session token"),
    language: str = Form("en", description="Language preference"),
    db: AsyncSession = Depends(get_db)
):
  
    try:
        # Log the entire request for debugging
        repo = SessionRepository(db)
        repo2 = ConversationMemoryRawRepository(db)
        print(session_token)

        
        user_id = await repo.get_user_id_by_session_id(session_token)
        rec = await repo2.create_new_session_with_welcome(user_id)

        # sess_id = await repo2.get_by_user_id()
        # count = await repo.delete_by_session_id(session_token)
        print(2)
        # user_record = await repo.create_session(user_id, session_token)
        return {"status": "success", "message": "Session refreshed successfully"} 
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in LTI launch GET: {e}")
        raise HTTPException(status_code=500, detail="LTI launch GET failed")

@router.post("/deep-linking")
async def lti_deep_linking(
    request: Request,
    id_token: str = Form(..., description="LTI ID token"),
    client_id: str = Form(..., description="Client ID")
):
    """LTI 1.3 deep linking endpoint"""
    try:
        logger.info(f"LTI deep linking request for client: {client_id}")
        
        # Verify LTI token
        is_valid, lti_payload = lti_service.verify_lti_request(id_token, client_id)
        
        if not is_valid:
            logger.error("LTI token verification failed")
            raise HTTPException(status_code=401, detail="Invalid LTI token")
        
        # Create deep linking response
        deep_linking_response = LTIDeepLinkingResponse(
            content_items=[
                {
                    "type": "ltiResourceLink",
                    "title": "AI Tutor",
                    "text": "AI-powered tutoring and assessment tool",
                    "url": str(request.base_url).rstrip('/') + "/lti/launch",
                    "icon": {
                        "url": str(request.base_url).rstrip('/') + "/static/ai-tutor-icon.png",
                        "width": 64,
                        "height": 64
                    },
                    "custom": {
                        "ai_tutor_enabled": "true",
                        "quiz_enabled": "true",
                        "conversation_enabled": "true"
                    }
                }
            ],
            data="ai_tutor_deep_linking",
            msg="AI Tutor tool configured successfully"
        )
        
        # Render deep linking response
        return templates.TemplateResponse(
            "lti_deep_linking.html",
            {
                "request": request,
                "deep_linking_response": deep_linking_response.dict()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in LTI deep linking: {e}")
        raise HTTPException(status_code=500, detail="LTI deep linking failed")

@router.get("/session/{session_token}")
async def get_lti_session(session_token: str):
    """Get LTI session data"""
    try:
        logger.info(f"Session lookup request for token: {session_token}")
        
        session_data = memory_service.get_lti_session(session_token)
        logger.info(f"Session data found: {session_data is not None}")
        
        if not session_data:
            logger.error(f"No session found for token: {session_token}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        logger.info(f"Session data keys: {list(session_data.keys()) if session_data else 'None'}")
        
        return {
            "status": "success",
            "session": session_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting LTI session: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session")

@router.get("/test-session/{session_token}")
async def test_lti_session(session_token: str):
    """Test endpoint to verify LTI session is working"""
    try:
        logger.info(f"Testing session: {session_token}")
        
        # Check if session exists
        session_data = memory_service.get_lti_session(session_token)
        if not session_data:
            logger.error(f"Session not found: {session_token}")
            return {
                "status": "error",
                "message": "Session not found",
                "session_token": session_token
            }
        
        logger.info(f"Session found: {session_data.keys()}")
        
        # Return simple test data
        return {
            "status": "success",
            "message": "Session is working",
            "session_token": session_token,
            "user_id": session_data.get("user_id"),
            "course_id": session_data.get("course_id"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Session test error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "session_token": session_token
        }

@router.get("/debug/sessions")
async def debug_sessions():
    """Debug endpoint to see all active sessions (for development only)"""
    try:
        # This is a development-only endpoint to help debug session issues
        # In production, you'd want to remove this or add proper authentication
        
        # Get all sessions from memory service (if available)
        # Note: This depends on your memory service implementation
        logger.info("Debug: Listing all active sessions")
        
        # For now, return a simple message
        return {
            "status": "debug",
            "message": "Debug endpoint active",
            "note": "Check backend logs for session information",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Debug sessions error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/debug/lti-payload")
async def debug_lti_payload():
    """Debug endpoint to show LTI payload structure (for development only)"""
    try:
        # This endpoint helps understand the LTI payload structure
        # In production, you'd want to remove this or add proper authentication
        
        return {
            "status": "debug",
            "message": "LTI payload debug endpoint",
            "note": "Check backend logs during LTI launch for detailed payload structure",
            "recommendations": [
                "Add custom_course_id=$Canvas.course.id to your LTI tool configuration",
                "Use $Context.id for LTI context identifier",
                "Check Canvas Variable Substitutions documentation"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Debug LTI payload error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@router.delete("/session/{session_token}")
async def delete_lti_session(session_token: str):
    """Delete LTI session"""
    try:
        memory_service.delete_lti_session(session_token)
        return {"message": "Session deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting LTI session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")

@router.post("/chat")
async def lti_chat(
    request: Request,
    message: str = Form(..., description="User message"),
    session_token: str = Form(..., description="LTI session token")
):
    """Chat endpoint for LTI users"""
    try:
        # Get LTI session
        session_data = memory_service.get_lti_session(session_token)
        
        if not session_data:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Create chat request
        chat_request = {
            "message": message,
            "user_id": session_data["user_id"],
            "course_id": session_data["course_id"],
            "language": "en"  # Default language, can be made configurable
        }
        
        # Generate AI response
        response = ai_service.generate_response(chat_request)
        
        return {"response": response}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in LTI chat: {e}")
        raise HTTPException(status_code=500, detail="Chat failed")

@router.get("/health")
async def lti_health():
    """LTI service health check"""
    try:
        # Check if keys are available
        keys_available = (
            lti_service.private_key is not None and 
            lti_service.public_key is not None
        )
        return {
            "status": "ok" if keys_available else "error",
            "service": "lti_service",
            "keys_available": keys_available,
            "kid": lti_service.kid,
            "platform_storage_enabled": lti_service.is_platform_storage_enabled(),
            "platform_storage_target": lti_service.get_platform_storage_target()
        }
        
    except Exception as e:
        logger.error(f"LTI health check error: {e}")
        return {
            "status": "error",
            "service": "lti_service",
            "error": str(e)
        }

@router.get("/icon")
async def lti_icon():
    """LTI tool icon endpoint for Canvas"""
    # Return a simple SVG icon as the response
    icon_svg = '''<svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="1" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
            </linearGradient>
        </defs>
        <rect width="32" height="32" rx="6" fill="url(#1)"/>
        <text x="16" y="22" font-family="Arial, sans-serif" font-size="18" font-weight="bold" text-anchor="middle" fill="white">AI</text>
    </svg>'''
    
    from fastapi.responses import Response
    return Response(
        content=icon_svg,
        media_type="image/svg+xml",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@router.options("/icon")
async def lti_icon_options():
    """CORS preflight for icon endpoint"""
    from fastapi.responses import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@router.get("/favicon.ico")
async def lti_favicon():
    """LTI tool favicon endpoint for Canvas"""
    # Return the same icon as favicon
    icon_svg = '''<svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="1" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
            </linearGradient>
        </defs>
        <rect width="32" height="32" rx="6" fill="url(#1)"/>
        <text x="16" y="22" font-family="Arial, sans-serif" font-size="18" font-weight="bold" text-anchor="middle" fill="white">AI</text>
    </svg>'''
    
    from fastapi.responses import Response
    return Response(
        content=icon_svg,
        media_type="image/svg+xml",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@router.post("/platform-storage/put")
async def platform_storage_put(
    request: Request,
    key: str = Form(..., description="Storage key"),
    value: str = Form(..., description="Storage value"),
    session_token: str = Form(..., description="LTI session token")
):
    """Platform Storage PUT endpoint for storing data"""
    try:
        # Verify session
        session_data = memory_service.get_lti_session(session_token)
        if not session_data:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Store data in platform storage
        storage_key = f"lti_storage_{session_data['user_id']}_{key}"
        success = memory_service.store_lti_storage(storage_key, value)
        
        if success:
            return {"status": "success", "message": "Data stored successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to store data")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Platform storage PUT error: {e}")
        raise HTTPException(status_code=500, detail="Platform storage operation failed")

@router.post("/platform-storage/get")
async def platform_storage_get(
    request: Request,
    key: str = Form(..., description="Storage key"),
    session_token: str = Form(..., description="LTI session token")
):
    """Platform Storage GET endpoint for retrieving data"""
    try:
        # Verify session
        session_data = memory_service.get_lti_session(session_token)
        if not session_data:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Retrieve data from platform storage
        storage_key = f"lti_storage_{session_data['user_id']}_{key}"
        value = memory_service.get_lti_storage(storage_key)
        
        if value is not None:
            return {"status": "success", "value": value}
        else:
            return {"status": "not_found", "value": None}
            
    except Exception as e:
        logger.error(f"Platform storage GET error: {e}")
        raise HTTPException(status_code=500, detail="Platform storage operation failed") 

@router.get("/course/progress/{session_token}")
async def get_course_progress(
    request: Request,
    session_token: str
):
    """Get course progress and module completion for LTI user"""
    try:
        logger.info(f"Course progress request for session: {session_token}")
        
        # Verify session
        session_data = memory_service.get_lti_session(session_token)
        logger.info(f"Session data retrieved: {session_data is not None}")
        
        if not session_data:
            logger.error(f"No session found for token: {session_token}")
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Get course summary using LTI AI service
        logger.info(f"Getting course summary for user: {session_data['user_id']}, course: {session_data['course_id']}")
        
        course_summary = lti_ai_service.get_course_summary(
            user_id=session_data["user_id"],
            course_id=session_data["course_id"],
            lti_context=session_data
        )
        
        logger.info(f"Course summary retrieved: {course_summary is not None}")
        if course_summary:
            logger.info(f"Course summary keys: {list(course_summary.keys())}")
        
        if "error" in course_summary:
            logger.error(f"Course summary error: {course_summary['error']}")
            raise HTTPException(status_code=500, detail=course_summary["error"])
        
        return course_summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting course progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to get course progress")

from app.api.setup_db import get_top_5_content
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException
from app.core.dependancies import get_db

@router.post("/course/chat")
async def lti_course_chat(
    request: Request,
    message: str = Form(..., description="User message"),
    session_token: str = Form(..., description="LTI session token"),
    language: str = Form("en", description="Language preference"),
    db: AsyncSession = Depends(get_db)
):
    """LTI course chat with Canvas progress context"""
    try:

        response = get_top_5_content(message, db)
        context = response['results']
        # Verify session
        logger.info(f"Course chat request for session: {session_token}")
        session_data = memory_service.get_lti_session(session_token)
        logger.info(f"Session data retrieved: {session_data is not None}")
        
        if not session_data:
            logger.error(f"No session found for token: {session_token}")
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Generate contextual AI response with Canvas progress
        logger.info(f"Generating AI response for message: {message[:50]}...")
        response = lti_ai_service.generate_contextual_response(
            message=message,
            user_id=session_data["user_id"],
            course_id=session_data["course_id"],
            lti_context=response,
            language=language
        )
        
        logger.info(f"AI response generated: {response is not None}")
        if response:
            logger.info(f"Response keys: {list(response.keys())}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in LTI course chat: {e}")
        raise HTTPException(status_code=500, detail="Course chat failed")

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
from app.services.summarize_conversation import summary_creator
from fastapi import BackgroundTasks

model = SentenceTransformer("all-MiniLM-L6-v2")

@dataclass
class TutorResponse:
    """Represents a response from the AI tutor"""
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    suggested_actions: List[str]
    learning_objectives: List[str]

@router.post("/course/chatv2")
async def lti_course_chat(
    request: Request,
    background_tasks: BackgroundTasks,
    message: str = Form(..., description="User message"),
    session_token: str = Form(..., description="LTI session token"),
    language: str = Form("en", description="Language preference"),
    db: AsyncSession = Depends(get_db)
):
    """LTI course chat with Canvas progress context"""
    try:

        tutor = AITutor()


        repo = SessionRepository(db)
        repo2 = ConversationMemoryRawRepository(db)
        print(1)
        user_id = await repo.get_user_id_by_session_id(session_token)
        print(2)
        user_record = await repo2.get_user_by_id(user_id)
        print(user_record)
        history = await repo2.format_conversations_for_chatbot(user_record['session_id'])
        
        

        # Initialize embedding model
        
        query_embedding = model.encode(message, convert_to_numpy=True, device='cpu').tolist()
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        params = {
            'user_id': user_id,
            'course_id': None,
            'module_item_id': None,
            'message': message,
            'message_from': 'user',
            'session_id': user_record['session_id'],
            'summary': None,
            'embedding': embedding_str
            # 'context_used': json.dumps(memory_data.get('context_used')) if memory_data.get('context_used') else None
        }

        rec = await repo2.create(params)

        logger.info('question added in conversation: ', rec)

        # Verify session
        logger.info(f"Course chat request for session: {session_token}")
        session_data = memory_service.get_lti_session(session_token)
        logger.info(f"Session data retrieved: {session_data is not None}")
        
        if not session_data:
            logger.error(f"No session found for token: {session_token}")
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Generate contextual AI response with Canvas progress
        previous_summary = await repo2.get_latest_summary(user_id)
        similar_convo = await repo2.find_similar_conversations(user_id, embedding_str)

        logger.info(f"Generating AI response for message: {message[:50]}...")
        response = await tutor.ask_question(
            question=message,
            history=history,
            summary=previous_summary,
            similar_past_convo=similar_convo,
            db=db
        )
        
        logger.info(f"AI response generated: {response is not None}")

        background_tasks.add_task(summary_creator.summerize, user_id, message, response.answer, previous_summary, user_record['session_id'], repo2)
        
        # summary = summary_creator.summerize(message, response.answer, previous_summary)
        
        # query_embedding = model.encode(response.answer, convert_to_numpy=True, device='cpu').tolist()
        # embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"



        # params = {
        #     'user_id': user_id,
        #     'course_id': None,
        #     'module_item_id': None,
        #     'message': response.answer,
        #     'message_from': 'ai',
        #     'session_id': user_record['session_id'],
        #     'summary': summary,
        #     'embedding': embedding_str
        # }

        # rec = await repo2.create(params)

        # logger.info('response added in conversation: ', rec)

        # print(response)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in LTI course chat: {e}")
        raise HTTPException(status_code=500, detail="Course chat failed")

@router.get("/course/modules/{session_token}")
async def get_course_modules(
    request: Request,
    session_token: str
):
    """Get course modules and structure for LTI user"""
    try:
        logger.info(f"Course modules request for session: {session_token}")
        
        # Verify session
        session_data = memory_service.get_lti_session(session_token)
        logger.info(f"Session data retrieved: {session_data is not None}")
        
        if not session_data:
            logger.error(f"No session found for token: {session_token}")
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # For now, use fallback course summary since Canvas API requires proper LTI Advantage setup
        # In production, this would use the actual Canvas API with proper OAuth2 tokens
        logger.info(f"Using fallback course modules for LTI user {session_data['user_id']} in course {session_data['course_id']}")
        
        from app.services.lti_ai_service import lti_ai_service
        course_summary = lti_ai_service.get_course_summary(
            user_id=session_data["user_id"],
            course_id=session_data["course_id"],
            lti_context=session_data
        )
        
        logger.info(f"Course summary retrieved: {course_summary is not None}")
        if course_summary:
            logger.info(f"Course summary keys: {list(course_summary.keys())}")
        
        if "error" in course_summary:
            logger.error(f"Course summary error: {course_summary['error']}")
            raise HTTPException(status_code=500, detail=course_summary["error"])
        
        # Extract modules from course summary
        modules = course_summary.get("modules", [])
        logger.info(f"Modules extracted: {len(modules)} modules")
        
        return {
            "course_id": session_data["course_id"],
            "modules": modules,
            "total_modules": len(modules),
            "source": "fallback_system",
            "note": "Using simulated course data. Enable Canvas API integration for real-time data."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting course modules: {e}")
        raise HTTPException(status_code=500, detail="Failed to get course modules")

@router.get("/course/current-context/{session_token}")
async def get_current_context(
    request: Request,
    session_token: str
):
    """Get current module context and recommendations for LTI user"""
    try:
        # Verify session
        session_data = memory_service.get_lti_session(session_token)
        if not session_data:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # For now, use fallback course summary since Canvas API requires proper LTI Advantage setup
        # In production, this would use the actual Canvas API with proper OAuth2 tokens
        logger.info(f"Using fallback current context for LTI user {session_data['user_id']} in course {session_data['course_id']}")
        
        from app.services.lti_ai_service import lti_ai_service
        course_summary = lti_ai_service.get_course_summary(
            user_id=session_data["user_id"],
            course_id=session_data["course_id"],
            lti_context=session_data
        )
        
        logger.info(f"Course summary retrieved: {course_summary is not None}")
        if course_summary:
            logger.info(f"Course summary keys: {list(course_summary.keys())}")
        
        if "error" in course_summary:
            logger.error(f"Course summary error: {course_summary['error']}")
            raise HTTPException(status_code=500, detail=course_summary["error"])
        
        # Extract current context from course summary
        current_context = course_summary.get("current_context", {})
        logger.info(f"Current context extracted: {current_context is not None}")
        
        # Extract recommended content from course summary
        recommended_content = course_summary.get("progress", {}).get("recommended_content", [])
        logger.info(f"Recommended content extracted: {len(recommended_content) if recommended_content else 0} items")
        
        return {
            "course_id": session_data["course_id"],
            "current_context": current_context,
            "recommended_content": recommended_content,
            "timestamp": datetime.now().isoformat(),
            "source": "fallback_system",
            "note": "Using simulated course data. Enable Canvas API integration for real-time data."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current context: {e}")
        raise HTTPException(status_code=500, detail="Failed to get current context") 