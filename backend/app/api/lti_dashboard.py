"""
LTI 1.3 Dashboard API Endpoints
"""
import logging
import json
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Form, Query, Depends
from fastapi.responses import RedirectResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from app.services.lti_dashboard_service import lti_dashboard_service
from app.services.memory_service import memory_service
from app.repository.conversation_memory import ConversationMemoryRawRepository
from sqlalchemy.ext.asyncio import AsyncSession
from app.repository.user_sessions import SessionRepository
from app.core.dependancies import get_db
from app.services.quiz_services import *

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/lti_dashboard", tags=["LTI 1.3 Dashboard"])

# Templates for LTI responses
templates = Jinja2Templates(directory="app/widgets")

@router.get("/config")
async def get_lti_dashboard_config(request: Request):
    """Get LTI 1.3 dashboard tool configuration"""
    try:
        base_url = str(request.base_url).rstrip('/')
        config = lti_dashboard_service.get_tool_configuration(base_url)
        
        # Modify config for dashboard
        config_dict = config.dict()
        config_dict["title"] = "AI Dashboard"
        config_dict["target_link_uri"] = f"{base_url}/lti_dashboard/launch"
        config_dict["oidc_initiation_url"] = f"{base_url}/lti_dashboard/oidc"
        
        return JSONResponse(content=config_dict)
        
    except Exception as e:
        logger.error(f"Error getting LTI dashboard config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get LTI dashboard configuration")

@router.get("/oidc")
async def oidc_initiation_get_dashboard(
    request: Request,
    iss: str = Query(..., description="Platform issuer"),
    login_hint: str = Query(..., description="Login hint"),
    target_link_uri: str = Query(..., description="Target link URI"),
    client_id: str = Query(..., description="Client ID"),
    lti_message_hint: Optional[str] = Query(None, description="LTI message hint")
):
    """OIDC initiation endpoint for LTI 1.3 Dashboard (GET method)"""
    try:
        logger.info(f"OIDC initiation GET for dashboard platform: {iss}, client: {client_id}")
        logger.info(f"Target link URI: {target_link_uri}")
        logger.info(f"Login hint: {login_hint}")
        logger.info(f"LTI message hint: {lti_message_hint}")
        
        # Generate state and nonce for security
        state = lti_dashboard_service.generate_nonce()
        nonce = lti_dashboard_service.generate_nonce()
        
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
        memory_service.store_lti_storage(f"oidc_state_dashboard_{state}", json.dumps(oidc_state))
        
        # Build OIDC authorization request to Canvas
        canvas_oidc_url = "https://sso.canvaslms.com/api/lti/authorize_redirect"
        
        # For LTI 1.3, the redirect_uri should be our launch endpoint
        # Canvas will send the id_token directly to our launch endpoint
        # Force HTTPS for redirect URI (Canvas requires HTTPS)
        base_url = str(request.base_url).rstrip('/')
        if base_url.startswith('http://'):
            base_url = base_url.replace('http://', 'https://')
        our_redirect_uri = base_url + "/lti_dashboard/launch"
        
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
async def oidc_initiation_post_dashboard(
    request: Request,
    iss: str = Form(..., description="Platform issuer"),
    login_hint: str = Form(..., description="Login hint"),
    target_link_uri: str = Form(..., description="Target link URI"),
    client_id: str = Form(..., description="Client ID"),
    lti_message_hint: Optional[str] = Form(None, description="LTI message hint")
):
    """OIDC initiation endpoint for LTI 1.3 Dashboard (POST method)"""
    try:
        logger.info(f"OIDC initiation POST for dashboard platform: {iss}, client: {client_id}")
        logger.info(f"Target link URI: {target_link_uri}")
        logger.info(f"Login hint: {login_hint}")
        logger.info(f"LTI message hint: {lti_message_hint}")
        
        # Generate state and nonce for security
        state = lti_dashboard_service.generate_nonce()
        nonce = lti_dashboard_service.generate_nonce()
        
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
        memory_service.store_lti_storage(f"oidc_state_dashboard_{state}", json.dumps(oidc_state))
        
        # Build OIDC authorization request to Canvas
        canvas_oidc_url = "https://sso.canvaslms.com/api/lti/authorize_redirect"
        
        # For LTI 1.3, the redirect_uri should be our launch endpoint
        # Canvas will send the id_token directly to our launch endpoint
        # Force HTTPS for redirect URI (Canvas requires HTTPS)
        base_url = str(request.base_url).rstrip('/')
        if base_url.startswith('http://'):
            base_url = base_url.replace('http://', 'https://')
        our_redirect_uri = base_url + "/lti_dashboard/launch"
        
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
async def oidc_callback_dashboard(
    request: Request,
    id_token: str = Form(..., description="ID token from Canvas"),
    state: str = Form(..., description="State parameter for validation"),
    client_id: str = Form(..., description="Client ID")
):
    """OIDC callback endpoint that receives the id_token from Canvas for dashboard"""
    try:
        logger.info(f"OIDC callback received for dashboard client: {client_id}")
        logger.info(f"State parameter: {state}")
        logger.info(f"ID token length: {len(id_token) if id_token else 0}")
        
        # Retrieve stored OIDC state for validation
        stored_state_key = f"oidc_state_dashboard_{state}"
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
        is_valid, lti_payload = lti_dashboard_service.verify_lti_request(id_token, client_id)
        
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
        session_data = lti_dashboard_service.create_lti_session(lti_payload)
        
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
async def lti_launch_dashboard(
    request: Request,
    id_token: Optional[str] = Form(None, description="LTI ID token"),
    client_id: Optional[str] = Form(None, description="Client ID"),
    state: Optional[str] = Form(None, description="State parameter from OIDC"),
    lti_storage_target: Optional[str] = Form(None, description="Platform storage target frame"),
    db: AsyncSession = Depends(get_db)
):
    """LTI 1.3 dashboard launch endpoint with Platform Storage support and OIDC handling"""
    try:
        # Log the entire request for debugging
        logger.info(f"LTI dashboard launch request received")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        
        # Check if this is an OIDC response (has state parameter)
        if state:
            logger.info(f"OIDC response detected with state: {state}")
            
            # Retrieve stored OIDC state for validation
            stored_state_key = f"oidc_state_dashboard_{state}"
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
            logger.error("Missing id_token in LTI dashboard launch request")
            raise HTTPException(status_code=400, detail="Missing id_token parameter")
        
        if not client_id:
            logger.error("Missing client_id in LTI dashboard launch request")
            raise HTTPException(status_code=400, detail="Missing client_id parameter")
        
        logger.info(f"LTI dashboard launch request for client: {client_id}")
        logger.info(f"ID token length: {len(id_token) if id_token else 0}")
        
        # Verify LTI token
        is_valid, lti_payload = lti_dashboard_service.verify_lti_request(id_token, client_id)
        
        if not is_valid:
            logger.error("LTI token verification failed")
            raise HTTPException(status_code=400, detail="Invalid LTI token")
        
        # Create LTI session
        session_data = lti_dashboard_service.create_lti_session(lti_payload)
        
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

        # Create session in database
        repo = ConversationMemoryRawRepository(db)
        repo2 = SessionRepository(db)

        rec = await repo2.create_session(session_data["user_id"], session_data["session_token"])
        logger.info(f"New Dashboard Session created for user: {session_data['user_id']} with Session ID: {session_data['session_token']}")
        
        # Get user context for dashboard
        user_context = {
            "user_id": session_data["user_id"],
            "course_id": session_data["course_id"],
            "user_name": session_data["user_name"],
            "user_roles": session_data["user_roles"]
        }

        # Get conversation context for dashboard
        context = await repo.format_conversations_for_chatbot(session_data["session_token"])

        print('dashboard user context: ', user_context)
        print('dashboard context', context)
        
        # Render LTI dashboard launch page
        return templates.TemplateResponse(
            "lti_course_widget_dashboard.html",
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
        logger.error(f"Error in LTI dashboard launch: {e}")
        raise HTTPException(status_code=500, detail="LTI dashboard launch failed")

@router.get("/course/metrics/{session_token}")
async def get_course_metrics_dashboard(
    request: Request,
    session_token: str
):
    """Get course metrics for dashboard"""
    try:
        logger.info(f"Course metrics request for session: {session_token}")
        
        # Verify session
        session_data = memory_service.get_lti_session(session_token)
        logger.info(f"Session data retrieved: {session_data is not None}")
        
        if not session_data:
            logger.error(f"No session found for token: {session_token}")
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Return mock metrics for now - in production, these would come from actual analytics
        metrics = {
            "active_users": 25,
            "ai_interactions": 150,
            "completion_rate": "78%",
            "average_score": "85",
            "time_spent": "12h 30m",
            "course_id": session_data["course_id"],
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Returning metrics: {metrics}")
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting course metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get course metrics")

@router.get("/course/activity/{session_token}")
async def get_course_activity_dashboard(
    request: Request,
    session_token: str
):
    """Get recent course activity for dashboard"""
    try:
        logger.info(f"Course activity request for session: {session_token}")
        
        # Verify session
        session_data = memory_service.get_lti_session(session_token)
        logger.info(f"Session data retrieved: {session_data is not None}")
        
        if not session_data:
            logger.error(f"No session found for token: {session_token}")
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Return mock activity for now - in production, these would come from actual activity logs
        activities = [
            {
                "title": "Student completed Module 1",
                "timestamp": "2 hours ago",
                "type": "completion"
            },
            {
                "title": "New AI interaction recorded",
                "timestamp": "4 hours ago",
                "type": "ai_interaction"
            },
            {
                "title": "Quiz submitted - Score: 85%",
                "timestamp": "6 hours ago",
                "type": "quiz"
            },
            {
                "title": "Course material accessed",
                "timestamp": "1 day ago",
                "type": "access"
            }
        ]
        
        activity_data = {
            "activities": activities,
            "course_id": session_data["course_id"],
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Returning {len(activities)} activities")
        return activity_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting course activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to get course activity")

@router.get("/session/{session_token}")
async def get_lti_dashboard_session(session_token: str):
    """Get LTI dashboard session data"""
    try:
        logger.info(f"Dashboard session lookup request for token: {session_token}")
        
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
        logger.error(f"Error getting LTI dashboard session: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session")

@router.get("/health")
async def lti_dashboard_health():
    """LTI dashboard service health check"""
    try:
        # Check if keys are available
        keys_available = (
            lti_dashboard_service.private_key is not None and 
            lti_dashboard_service.public_key is not None
        )
        return {
            "status": "ok" if keys_available else "error",
            "service": "lti_dashboard_service",
            "keys_available": keys_available,
            "kid": lti_dashboard_service.kid,
            "platform_storage_enabled": lti_dashboard_service.is_platform_storage_enabled(),
            "platform_storage_target": lti_dashboard_service.get_platform_storage_target()
        }
        
    except Exception as e:
        logger.error(f"LTI dashboard health check error: {e}")
        return {
            "status": "error",
            "service": "lti_dashboard_service",
            "error": str(e)
        }

@router.get("/icon")
async def lti_dashboard_icon():
    """LTI dashboard tool icon endpoint for Canvas"""
    # Return a simple SVG icon as the response
    icon_svg = '''<svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="1" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#28a745;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#20c997;stop-opacity:1" />
            </linearGradient>
        </defs>
        <rect width="32" height="32" rx="6" fill="url(#1)"/>
        <text x="16" y="22" font-family="Arial, sans-serif" font-size="18" font-weight="bold" text-anchor="middle" fill="white">📊</text>
    </svg>'''
    
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
async def lti_dashboard_icon_options():
    """CORS preflight for icon endpoint"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@router.get("/favicon.ico")
async def lti_dashboard_favicon():
    """LTI dashboard tool favicon endpoint for Canvas"""
    # Return the same icon as favicon
    icon_svg = '''<svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="1" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#28a745;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#20c997;stop-opacity:1" />
            </linearGradient>
        </defs>
        <rect width="32" height="32" rx="6" fill="url(#1)"/>
        <text x="16" y="22" font-family="Arial, sans-serif" font-size="18" font-weight="bold" text-anchor="middle" fill="white">📊</text>
    </svg>'''
    
    return Response(
        content=icon_svg,
        media_type="image/svg+xml",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )
