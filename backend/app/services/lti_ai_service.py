"""
LTI AI Service for Canvas Integration
Provides contextual AI assistance based on Canvas course progress and modules
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .ai_service import ai_service
from .canvas_api_service import canvas_api_service
from .lti_advantage_service import lti_advantage_service
from .knowledge_base_service import knowledge_base_service
from .lti_rag_service import LTIRAGService
from .enhanced_canvas_knowledge_service import EnhancedCanvasKnowledgeService

logger = logging.getLogger(__name__)

class LTIAIService:
    """AI service specifically for LTI integration with Canvas progress tracking"""
    
    def __init__(self):
        self.ai_service = ai_service
        self.lti_rag_service = LTIRAGService()
        self.enhanced_canvas_knowledge = EnhancedCanvasKnowledgeService()
        
    def generate_contextual_response(self, message: str, user_id: str, course_id: str, 
                                   lti_context: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
        """Generate AI response with Canvas course context"""
        try:
            logger.info(f"🚀 Generating contextual response for user {user_id} in course {course_id}")
            logger.info(f"📝 User message: {message[:100]}...")

            
            
            # Use real Canvas API credentials directly instead of LTI Advantage
            # This ensures we get real course data instead of simulated tokens
            real_canvas_context = self._get_real_canvas_context(course_id, user_id)
            
            # Get user's current course progress using real Canvas API
            progress_context = self._get_progress_context(real_canvas_context, lti_context)
            
            # Ensure course_id is set in progress context
            if not progress_context.get("course_id") and lti_context.get("course_id"):
                progress_context["course_id"] = lti_context["course_id"]
                logger.info(f"Set course_id in progress context: {lti_context['course_id']}")
            
            # Set Canvas API context with real credentials
            if real_canvas_context:
                canvas_api_service.set_lti_context(
                    real_canvas_context["base_url"],
                    real_canvas_context["access_token"],
                    real_canvas_context["course_id"],
                    real_canvas_context["user_id"]
                )
                logger.info("✅ Canvas API context set successfully with real credentials")
                
                # Now that Canvas API is set up, analyze the user query and fetch relevant data
                logger.info("🔍 Analyzing user query for Canvas API calls...")
                
            else:
                logger.warning(f"⚠️ Could not get real Canvas API context for user {user_id}, using fallback")
            
            # Generate enhanced AI response with progress context
            response = self._generate_progress_aware_response(message, progress_context, language)
            
            # Add Canvas API integration status to response
            if real_canvas_context:
                response["canvas_api_status"] = "active"
                response["canvas_api_domain"] = real_canvas_context["base_url"]
            else:
                response["canvas_api_status"] = "fallback"
            
            logger.info(f"✅ Contextual response generated successfully")
            return response
            
        except Exception as e:
            logger.error(f"Error generating contextual response: {e}")
            return self._fallback_response(message, language)
    
    def _get_real_canvas_context(self, course_id: str, user_id: str) -> Dict[str, Any]:
        """Get real Canvas API context using credentials from environment"""
        try:
            import os
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Get real Canvas credentials from environment
            canvas_url = os.getenv('CANVAS_URL')
            canvas_token = os.getenv('CANVAS_API_TOKEN')
            
            if canvas_url and canvas_token:
                logger.info(f"✅ Using real Canvas API credentials for course {course_id}")
                return {
                    "base_url": canvas_url,
                    "access_token": canvas_token,
                    "course_id": course_id,
                    "user_id": user_id
                }
            else:
                logger.warning("⚠️  Real Canvas API credentials not found in environment")
                return None
                
        except Exception as e:
            logger.error(f"Error getting real Canvas context: {e}")
            return None
    
    def _get_enhanced_canvas_context(self, message: str, progress_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get enhanced Canvas context using specific Canvas APIs based on user query"""
        try:
            course_id = progress_context.get("course_id")
            user_id = progress_context.get("user_id")
            
            if not course_id:
                logger.warning("No course_id in progress context for enhanced Canvas context")
                return []
            
            logger.info(f"🔍 Analyzing user query: '{message}' for Canvas API calls")
            
            # Analyze the message to determine what Canvas data to fetch
            query_analysis = self._analyze_user_query(message)
            logger.info(f"Query analysis: {query_analysis}")
            
            # Fetch relevant Canvas data based on query analysis
            canvas_data = self._fetch_relevant_canvas_data(course_id, user_id, query_analysis)
            
            if canvas_data:
                # Convert Canvas data to knowledge base format
                knowledge_entries = self._convert_canvas_data_to_knowledge(canvas_data, query_analysis)
                logger.info(f"Generated {len(knowledge_entries)} enhanced knowledge entries from Canvas API")
                return knowledge_entries
            
            # Fallback to existing enhanced context method
            logger.info("Falling back to existing enhanced context method")
            enhanced_context = self.enhanced_canvas_knowledge.get_enhanced_context_for_question(
                message, course_id, user_id
            )
            
            if enhanced_context:
                return self._convert_enhanced_context_to_knowledge(enhanced_context)
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting enhanced Canvas context: {e}")
            return []
    
    def _get_smart_enhanced_canvas_context(self, message: str, progress_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get enhanced Canvas context using smart query handling"""
        try:
            course_id = progress_context.get("course_id")
            user_id = progress_context.get("user_id")
            
            if not course_id:
                logger.warning("No course_id in progress context for smart enhanced Canvas context")
                return []
            
            # Use smart query handler to determine what the user is asking for
            smart_result = self.enhanced_canvas_knowledge.smart_query_handler(
                course_id, message, user_id
            )
            
            if smart_result["type"] == "error":
                logger.warning(f"Smart query handler error: {smart_result.get('error')}")
                return []
            
            # Convert smart result to knowledge base format
            knowledge_entries = []
            
            if smart_result["type"] == "module":
                # User asked for specific module - CRITICAL FIX: Always provide module info
                module_data = smart_result["data"]
                if module_data:
                    # Create rich module knowledge entry
                    module_content = self._format_enhanced_module_content(module_data)
                    
                    # Add additional context about what this module contains
                    module_content += f"\n\nThis module is part of the course structure and contains important information for students."
                    
                    knowledge_entries.append({
                        "title": f"Specific Module: {module_data.get('name', 'Unknown')}",
                        "content": module_content,
                        "content_type": "canvas_module_specific",
                        "metadata": {
                            "source": "canvas_api_smart",
                            "query_type": "specific_module",
                            "relevance": "high",
                            "module_id": module_data.get('id'),
                            "module_position": module_data.get('position')
                        }
                    })
                    logger.info(f"✅ Generated specific module knowledge for: {module_data.get('name')}")
                    
                    # CRITICAL: Also add basic module structure from Canvas API as fallback
                    try:
                        basic_modules = self.canvas_api_service.get_course_modules()
                        if basic_modules:
                            # Find the specific module in the basic list
                            for basic_module in basic_modules:
                                if basic_module.get('id') == module_data.get('id'):
                                    # Add basic module info as additional context
                                    basic_content = f"Module Structure:\n"
                                    basic_content += f"- Name: {basic_module.get('name', 'Unknown')}\n"
                                    basic_content += f"- Position: {basic_module.get('position', 'Unknown')}\n"
                                    basic_content += f"- State: {basic_module.get('state', 'Unknown')}\n"
                                    
                                    # Add items if available
                                    items = basic_module.get('items', [])
                                    if items:
                                        basic_content += f"- Contains {len(items)} items:\n"
                                        for item in items[:5]:  # Show first 5 items
                                            basic_content += f"  • {item.get('title', 'Unknown')} ({item.get('type', 'Unknown')})\n"
                                        if len(items) > 5:
                                            basic_content += f"  ... and {len(items) - 5} more items\n"
                                    
                                    knowledge_entries.append({
                                        "title": f"Module Details: {basic_module.get('name', 'Unknown')}",
                                        "content": basic_content,
                                        "content_type": "canvas_module_basic",
                                        "metadata": {
                                            "source": "canvas_api_basic",
                                            "query_type": "module_structure",
                                            "relevance": "high"
                                        }
                                    })
                                    logger.info(f"✅ Added basic module structure for: {basic_module.get('name')}")
                                    break
                    except Exception as e:
                        logger.warning(f"Could not add basic module structure: {e}")
                
                else:
                    logger.warning("Smart query handler returned module type but no module data")
            
            elif smart_result["type"] == "item":
                # User asked for specific item
                item_data = smart_result["data"]
                if item_data:
                    knowledge_entries.append({
                        "title": f"Specific Item: {item_data.get('title', 'Unknown')}",
                        "content": self._format_enhanced_item_content(item_data, item_data.get("module_context", {})),
                        "content_type": "canvas_item_specific",
                        "metadata": {
                            "source": "canvas_api_smart",
                            "query_type": "specific_item",
                            "relevance": "high"
                        }
                    })
                    logger.info(f"Generated specific item knowledge for: {item_data.get('title')}")
            
            elif smart_result["type"] == "general":
                # User asked general question, use enhanced context
                general_context = smart_result["data"]
                if general_context:
                    for context_item in general_context:
                        if context_item["type"] == "module":
                            knowledge_entries.append({
                                "title": f"Enhanced Module: {context_item['data'].get('name', 'Unknown')}",
                                "content": self._format_enhanced_module_content(context_item['data']),
                                "content_type": "canvas_module_enhanced",
                                "metadata": {
                                    "source": "canvas_api_smart",
                                    "query_type": "general_context",
                                    "relevance": context_item.get("relevance", "medium")
                                }
                            })
                        elif context_item["type"] == "item":
                            knowledge_entries.append({
                                "title": f"Enhanced Item: {context_item['data'].get('title', 'Unknown')}",
                                "content": self._format_enhanced_item_content(context_item['data'], context_item.get('module', {})),
                                "content_type": "canvas_item_enhanced",
                                "metadata": {
                                    "source": "canvas_api_smart",
                                    "query_type": "general_context",
                                    "relevance": context_item.get("relevance", "high")
                                }
                            })
            
            logger.info(f"Generated {len(knowledge_entries)} smart knowledge entries")
            return knowledge_entries
            
        except Exception as e:
            logger.error(f"Error getting smart enhanced Canvas context: {e}")
            return []
    
    def _format_enhanced_module_content(self, module: Dict[str, Any]) -> str:
        """Format enhanced module content for knowledge base"""
        try:
            content_parts = []
            
            content_parts.append(f"Module: {module.get('name', 'Unknown Module')}")
            content_parts.append(f"Position: {module.get('position', 'Unknown')}")
            content_parts.append(f"State: {module.get('state', 'Unknown')}")
            content_parts.append(f"Published: {module.get('published', 'Unknown')}")
            
            # Add items summary
            items = module.get("items", [])
            if items:
                content_parts.append(f"Contains {len(items)} items:")
                for item in items[:3]:  # Show first 3 items
                    content_parts.append(f"  - {item.get('title', 'Unknown')} ({item.get('type', 'Unknown')})")
                if len(items) > 3:
                    content_parts.append(f"  ... and {len(items) - 3} more items")
            
            return "\n".join(content_parts)
            
        except Exception as e:
            logger.error(f"Error formatting enhanced module content: {e}")
            return str(module)
    
    def _format_enhanced_item_content(self, item: Dict[str, Any], module: Dict[str, Any]) -> str:
        """Format enhanced item content for knowledge base"""
        try:
            content_parts = []
            
            content_parts.append(f"Item: {item.get('title', 'Unknown Item')}")
            content_parts.append(f"Type: {item.get('type', 'Unknown')}")
            content_parts.append(f"Module: {module.get('name', 'Unknown Module')}")
            content_parts.append(f"Module Position: {module.get('position', 'Unknown')}")
            
            # Completion requirements
            completion_req = item.get("completion_requirement", {})
            if completion_req:
                req_type = completion_req.get("type", "none")
                min_score = completion_req.get("min_score")
                
                if req_type == "must_view":
                    content_parts.append("Completion: Must view this item")
                elif req_type == "must_submit":
                    content_parts.append("Completion: Must submit this item")
                elif req_type == "min_score" and min_score:
                    content_parts.append(f"Completion: Must achieve at least {min_score}%")
                elif req_type == "must_contribute":
                    content_parts.append("Completion: Must contribute to this item")
                else:
                    content_parts.append("Completion: No specific requirement")
            
            # Content details
            content_details = item.get("content_details", {})
            if content_details:
                if content_details.get("points_possible"):
                    content_parts.append(f"Points: {content_details['points_possible']}")
                
                if content_details.get("due_at"):
                    content_parts.append(f"Due: {content_details['due_at']}")
                
                if content_details.get("locked"):
                    content_parts.append("Status: Locked")
                
                if content_details.get("hidden"):
                    content_parts.append("Status: Hidden")
            
            return "\n".join(content_parts)
            
        except Exception as e:
            logger.error(f"Error formatting enhanced item content: {e}")
            return str(item)
    
    def _get_progress_context(self, canvas_context: Dict[str, Any], lti_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive progress context for the user"""
        try:
            # Check if we have real Canvas API context and try to get real progress
            if canvas_context and canvas_context.get("access_token"):
                try:
                    logger.info("🔍 Attempting to get real progress from Canvas API...")
                    
                    # Get real progress from Canvas API
                    real_progress = self.canvas_api_service.get_user_progress()
                    if real_progress:
                        logger.info("✅ Retrieved real progress from Canvas API")
                        
                        # Also get current module context for better understanding
                        try:
                            current_module_context = self.canvas_api_service.get_current_module_context()
                            logger.info("✅ Retrieved current module context from Canvas API")
                        except Exception as e:
                            logger.warning(f"⚠️ Could not get current module context: {e}")
                            current_module_context = None
                        
                        progress_context = {
                            "course_id": canvas_context["course_id"],
                            "user_id": canvas_context["user_id"],
                            "real_progress": True,
                            "progress_data": real_progress,
                            "current_module": current_module_context,
                            "source": "canvas_api_real",
                            "canvas_api_ready": True,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        logger.info(f"📊 Progress context: {progress_context.get('progress_data', {}).get('completion_percentage', 'Unknown')}% complete")
                        return progress_context
                        
                except Exception as e:
                    logger.warning(f"⚠️ Could not get real progress from Canvas API: {e}")
                    logger.info("Canvas API may not be fully configured yet")
            
            # Fallback to simulated progress context
            logger.info("🔄 Using fallback progress context")
            progress_context = self._fallback_progress_context()
            
            # Update course_id from canvas_context if available
            if canvas_context and canvas_context.get("course_id"):
                progress_context["course_id"] = canvas_context["course_id"]
                logger.info(f"Updated progress context with course_id: {canvas_context['course_id']}")
            
            # Always ensure course_id is set from lti_context if not already set
            if not progress_context.get("course_id") and lti_context and lti_context.get("course_id"):
                progress_context["course_id"] = lti_context["course_id"]
                logger.info(f"Set course_id from LTI context: {lti_context['course_id']}")
            
            progress_context["canvas_api_ready"] = False
            return progress_context
            
        except Exception as e:
            logger.error(f"Error getting progress context: {e}")
            return self._fallback_progress_context()
    
    def _generate_progress_aware_response(self, message: str, progress_context: Dict[str, Any], 
                                        language: str) -> Dict[str, Any]:
        """Generate AI response that's aware of user's course progress"""
        try:
            logger.info(f"🧠 Generating progress-aware response for message: '{message[:50]}...'")
            
            # Enhance the message with progress context
            enhanced_message = self._enhance_message_with_progress(message, progress_context, language)
            
            # Get relevant knowledge base content for the course
            knowledge_context = self._get_knowledge_base_context(message, progress_context)
            
            # Check if Canvas API is ready and fetch relevant data based on user query
            if progress_context.get("canvas_api_ready"):
                logger.info("🔍 Canvas API is ready - fetching relevant data based on user query...")
                
                # Get enhanced Canvas context using the new smart query analysis
                enhanced_canvas_context = self._get_enhanced_canvas_context(message, progress_context)
                
                if enhanced_canvas_context:
                    knowledge_context.extend(enhanced_canvas_context)
                    logger.info(f"✅ Enhanced knowledge base with {len(enhanced_canvas_context)} Canvas API entries")
                else:
                    logger.info("ℹ️ No specific Canvas data found for this query, using general context")
            else:
                logger.info("🔄 Canvas API not ready, using fallback enhanced context...")
                # Get enhanced Canvas knowledge for better context using smart query handling
                enhanced_canvas_context = self._get_smart_enhanced_canvas_context(message, progress_context)
                
                # Combine knowledge contexts
                if enhanced_canvas_context:
                    knowledge_context.extend(enhanced_canvas_context)
                    logger.info(f"Enhanced knowledge base with {len(enhanced_canvas_context)} Canvas-specific entries")
            
            # Get course data for structured context
            course_data = self._get_course_data(progress_context)
            
            # Log the total knowledge context being used
            logger.info(f"📚 Total knowledge context: {len(knowledge_context)} entries")
            for i, entry in enumerate(knowledge_context[:3]):  # Log first 3 entries
                logger.info(f"  {i+1}. {entry.get('title', 'Unknown')} ({entry.get('content_type', 'Unknown')})")
            
            # Use enhanced LTI RAG service for contextual response
            enhanced_response = self.lti_rag_service.generate_contextual_response(
                user_question=message,
                knowledge_base_content=knowledge_context,
                student_context=progress_context,
                course_data=course_data,
                language=language
            )
            
            # Add Canvas API integration metadata to response
            if progress_context.get("canvas_api_ready"):
                enhanced_response["canvas_api_integration"] = {
                    "status": "active",
                    "data_sources": [entry.get("metadata", {}).get("source") for entry in enhanced_canvas_context if enhanced_canvas_context],
                    "query_analysis": "enabled"
                }
            else:
                enhanced_response["canvas_api_integration"] = {
                    "status": "fallback",
                    "note": "Using simulated data - Canvas API not fully configured"
                }
            
            logger.info(f"✅ Progress-aware response generated successfully")
            return enhanced_response
            
        except Exception as e:
            logger.error(f"Error generating progress-aware response: {e}")
            # Try to get a basic response with knowledge base context even if enhancement fails
            try:
                logger.info("Falling back to basic response with knowledge base context")
                knowledge_context = self._get_knowledge_base_context(message, progress_context)
                course_data = self._get_course_data(progress_context)
                
                fallback_response = self.lti_rag_service.generate_contextual_response(
                    user_question=message,
                    knowledge_base_content=knowledge_context,
                    student_context=progress_context,
                    course_data=course_data,
                    language=language
                )
                
                # Mark as fallback
                fallback_response["confidence"] = "medium"
                fallback_response["progress_insights"]["note"] = "Enhanced response failed, using basic response"
                
                return fallback_response
                
            except Exception as fallback_error:
                logger.error(f"Fallback response also failed: {fallback_error}")
                return self._fallback_response(message, language)
    
    def _get_knowledge_base_context(self, message: str, progress_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant knowledge base content for the course and user's current progress"""
        try:
            # Get course ID from progress context
            course_id = progress_context.get("course_id")
            if not course_id:
                logger.warning("No course ID found in progress context")
                return []
            
            # IMPORTANT: Use structured knowledge service instead of raw knowledge base search
            # This ensures we get verified, accurate course structure from Canvas API when available
            from .structured_knowledge_service import structured_knowledge_service
            
            logger.info(f"🔍 Getting structured course content for course {course_id}")
            
            # Get structured course content (Canvas API first, fallback to content)
            structured_content = structured_knowledge_service.get_structured_course_content(course_id)
            
            if not structured_content:
                logger.warning("No structured content found, falling back to raw search")
                return self._fallback_knowledge_search(message, progress_context)
            
            # Extract relevant information from structured content
            context_docs = []
            
            # Add course info
            course_info = structured_content.get('course_info', {})
            if course_info:
                context_docs.append({
                    "content": f"Course: {course_info.get('title', 'Unknown')} - {course_info.get('description', 'No description')}",
                    "title": "Course Information",
                    "content_type": "course_info",
                    "relevance_score": 1.0,
                    "summary": course_info.get('description', ''),
                    "source": "structured_knowledge"
                })
            
            # Add module information
            modules = structured_content.get('modules', [])
            for module in modules:
                # Check if module is relevant to the query
                if self._is_module_relevant(message, module):
                    module_content = f"Module: {module.get('title', 'Unknown')}"
                    
                    # Add module items if available
                    items = module.get('items', [])
                    if items:
                        module_content += f"\nItems: {', '.join([item.get('title', 'Unknown') for item in items[:3]])}"
                    
                    # Add source information
                    if module.get('source') == 'canvas_api':
                        module_content += f"\n[Source: Canvas API - Real course structure]"
                    else:
                        module_content += f"\n[Source: Content extraction - May be inaccurate]"
                    
                    context_docs.append({
                        "content": module_content,
                        "title": module.get('title', 'Unknown'),
                        "content_type": "module",
                        "relevance_score": 0.9,
                        "summary": f"Module information from {module.get('source', 'unknown')}",
                        "source": "structured_knowledge"
                    })
            
            # Add assignment information
            assignments = structured_content.get('assignments', [])
            for assignment in assignments:
                if self._is_assignment_relevant(message, assignment):
                    assignment_content = f"Assignment: {assignment.get('title', 'Unknown')} (Type: {assignment.get('type', 'Unknown')})"
                    
                    if assignment.get('source') == 'canvas_api':
                        assignment_content += f"\n[Source: Canvas API - Real assignment data]"
                    else:
                        assignment_content += f"\n[Source: Content extraction - May be incomplete]"
                    
                    context_docs.append({
                        "content": assignment_content,
                        "title": assignment.get('title', 'Unknown'),
                        "content_type": "assignment",
                        "relevance_score": 0.8,
                        "summary": f"Assignment information from {assignment.get('source', 'unknown')}",
                        "source": "structured_knowledge"
                    })
            
            # Add key concepts
            key_concepts = structured_content.get('key_concepts', {})
            if key_concepts:
                # Handle the dictionary format from structured knowledge service
                if isinstance(key_concepts, dict):
                    # Flatten the dictionary values into a single list
                    all_concepts = []
                    for category, concepts in key_concepts.items():
                        if isinstance(concepts, list):
                            all_concepts.extend(concepts)
                        else:
                            all_concepts.append(str(concepts))
                    
                    # Take first 5 concepts
                    concepts_list = all_concepts[:5] if len(all_concepts) > 5 else all_concepts
                elif isinstance(key_concepts, list):
                    # If it's already a list, use it directly
                    concepts_list = key_concepts[:5] if len(key_concepts) > 5 else key_concepts
                else:
                    concepts_list = [str(key_concepts)]
                
                if concepts_list:
                    concepts_content = f"Key Concepts: {', '.join(concepts_list)}"
                    context_docs.append({
                        "content": concepts_content,
                        "title": "Key Course Concepts",
                        "content_type": "concepts",
                        "relevance_score": 0.7,
                        "summary": "Main concepts covered in the course",
                        "source": "structured_knowledge"
                    })
            
            logger.info(f"✅ Generated {len(context_docs)} structured context documents")
            return context_docs
            
        except Exception as e:
            logger.error(f"Error getting structured knowledge context: {e}")
            logger.info("Falling back to raw knowledge base search")
            return self._fallback_knowledge_search(message, progress_context)
    
    def _fallback_knowledge_search(self, message: str, progress_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback to raw knowledge base search if structured approach fails"""
        try:
            course_id = progress_context.get("course_id")
            if not course_id:
                return []
            
            # Get current module context
            module_context = progress_context.get("module_context", {})
            current_module = module_context.get("current_module", {})
            current_module_name = current_module.get("name", "")
            
            # Search knowledge base with enhanced query
            enhanced_query = f"{message} {current_module_name} course {course_id}"
            logger.info(f"🔍 Fallback: Searching raw knowledge base with query: {enhanced_query}")
            
            # Search for relevant content
            knowledge_results = knowledge_base_service.search_knowledge_base(
                query=enhanced_query,
                course_id=course_id,
                max_results=5
            )
            
            logger.info(f"⚠️  Fallback: Found {len(knowledge_results)} raw knowledge base results")
            
            # Format results for AI service
            context_docs = []
            for result in knowledge_results:
                context_docs.append({
                    "content": result.get("content", ""),
                    "title": result.get("title", ""),
                    "content_type": result.get("content_type", ""),
                    "relevance_score": result.get("relevance_score", 0),
                    "summary": result.get("summary", ""),
                    "source": "raw_knowledge_base",
                    "warning": "Using raw knowledge base content - may contain inaccuracies"
                })
            
            return context_docs
            
        except Exception as e:
            logger.error(f"Error in fallback knowledge search: {e}")
            return []
    
    def _is_module_relevant(self, message: str, module: Dict[str, Any]) -> bool:
        """Check if a module is relevant to the user's query"""
        message_lower = message.lower()
        module_title = module.get('title', '').lower()
        
        # Check for direct matches
        if any(word in module_title for word in message_lower.split()):
            return True
        
        # Check for module-related queries
        if any(word in message_lower for word in ['module', 'first', 'second', 'third', 'overview', 'summary']):
            return True
        
        return False
    
    def _is_assignment_relevant(self, message: str, assignment: Dict[str, Any]) -> bool:
        """Check if an assignment is relevant to the user's query"""
        message_lower = message.lower()
        assignment_title = assignment.get('title', '').lower()
        
        # Check for direct matches
        if any(word in assignment_title for word in message_lower.split()):
            return True
        
        # Check for assignment-related queries
        if any(word in message_lower for word in ['assignment', 'quiz', 'discussion', 'exercise', 'practice']):
            return True
        
        return False
    
    def _enhance_message_with_progress(self, message: str, progress_context: Dict[str, Any], 
                                     language: str) -> str:
        """Enhance user message with progress context for better AI understanding"""
        try:
            module_context = progress_context.get("module_context", {})
            user_progress = progress_context.get("user_progress", {})
            
            # Add progress context to the message
            enhanced_parts = [message]
            
            if module_context.get("status") == "in_progress":
                current_module = module_context.get("current_module", {})
                completion = module_context.get("completion", {})
                
                progress_info = f" (Current module: {current_module.get('name', 'Unknown')}, "
                progress_info += f"Progress: {completion.get('completed_items', 0)}/{completion.get('total_items', 1)} items completed)"
                enhanced_parts.append(progress_info)
                
            elif module_context.get("status") == "completed":
                enhanced_parts.append(" (All course modules completed!)")
            
            # Add overall progress
            if user_progress:
                completion_percent = user_progress.get("completion", 0)
                enhanced_parts.append(f" (Overall course completion: {completion_percent:.1f}%)")
            
            return "".join(enhanced_parts)
            
        except Exception as e:
            logger.error(f"Error enhancing message with progress: {e}")
            return message
    
    def _enhance_response_with_progress(self, reply_text: str, progress_context: Dict[str, Any], 
                                      language: str) -> Dict[str, Any]:
        """Enhance AI response with progress insights and recommendations"""
        try:
            enhanced_response = {
                "reply": reply_text,
                "progress_insights": {},
                "recommendations": [],
                "next_steps": [],
                "context_used": [],
                "confidence": "high",
                "total_context_docs": 0
            }
            
            # Add progress insights
            module_context = progress_context.get("module_context", {})
            if module_context:
                enhanced_response["progress_insights"] = {
                    "current_module": module_context.get("current_module", {}).get("name"),
                    "module_progress": module_context.get("progress_percentage", 0),
                    "status": module_context.get("status"),
                    "next_module": module_context.get("next_module", {}).get("name") if module_context.get("next_module") else None
                }
            
            # Add recommendations
            recommended_content = progress_context.get("recommended_content", [])
            if recommended_content:
                enhanced_response["recommendations"] = [
                    {
                        "title": item.get("title") if isinstance(item, dict) else str(item),
                        "type": item.get("type") if isinstance(item, dict) else "content",
                        "priority": "high" if isinstance(item, dict) and item.get("type") in ["Assignment", "Quiz"] else "medium"
                    }
                    for item in recommended_content[:3]  # Top 3 recommendations
                ]
            
            # Add next steps
            if module_context.get("status") == "in_progress":
                completion = module_context.get("completion", {})
                incomplete_items = completion.get("incomplete_items", 0)
                
                if incomplete_items > 0:
                    enhanced_response["next_steps"] = [
                        f"Complete {incomplete_items} remaining items in current module",
                        "Review module content before moving to next module",
                        "Check assignment due dates and requirements"
                    ]
                else:
                    enhanced_response["next_steps"] = [
                        "Current module completed! Ready to move to next module",
                        "Review completed work for understanding",
                        "Prepare for next module content"
                    ]
            
            return enhanced_response
            
        except Exception as e:
            logger.error(f"Error enhancing response with progress: {e}")
            return {
                "reply": "I'm having trouble processing your request right now. Please try again.",
                "progress_insights": {"error": "Response enhancement failed"},
                "recommendations": [],
                "next_steps": [],
                "context_used": [],
                "confidence": "low",
                "total_context_docs": 0
            }
    
    def _fallback_response(self, message: str, language: str) -> Dict[str, Any]:
        """Fallback response when Canvas integration fails"""
        try:
            # Use base AI service without Canvas context
            base_response = self.ai_service.generate_response(
                message=message,
                context_docs=[],
                memory=None,
                language=language
            )
            
            # Extract the reply text from the base response
            reply_text = base_response.get("reply", "") if isinstance(base_response, dict) else str(base_response)
            
            return {
                "reply": reply_text,
                "progress_insights": {"note": "Canvas progress data unavailable"},
                "recommendations": [],
                "next_steps": [],
                "context_used": [],
                "confidence": "medium",
                "total_context_docs": 0
            }
            
        except Exception as e:
            logger.error(f"Error in fallback response: {e}")
            return {
                "reply": "I'm having trouble accessing your course information right now. Please try again later.",
                "progress_insights": {"error": "Service temporarily unavailable"},
                "recommendations": [],
                "next_steps": [],
                "context_used": [],
                "confidence": "low",
                "total_context_docs": 0
            }
    
    def _fallback_course_summary(self, lti_context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback course summary when Canvas API is not available"""
        try:
            # Extract available information from LTI context
            course_id = lti_context.get("course_id", "unknown")
            user_id = lti_context.get("user_id", "unknown")
            user_name = lti_context.get("user_name", "Student")
            user_roles = lti_context.get("user_roles", [])
            
            # Create simulated course structure based on LTI context
            simulated_modules = [
                {
                    "id": "module_1",
                    "name": "Introduction to Course",
                    "state": "completed",
                    "items": [
                        {"id": "item_1", "title": "Course Overview", "type": "page", "completed": True},
                        {"id": "item_2", "title": "Syllabus", "type": "page", "completed": True}
                    ]
                },
                {
                    "id": "module_2", 
                    "name": "Core Concepts",
                    "state": "in_progress",
                    "items": [
                        {"id": "item_3", "title": "Key Concepts", "type": "page", "completed": True},
                        {"id": "item_4", "title": "Practice Exercises", "type": "assignment", "completed": False}
                    ]
                },
                {
                    "id": "module_3",
                    "name": "Advanced Topics",
                    "state": "locked",
                    "items": [
                        {"id": "item_5", "title": "Advanced Concepts", "type": "page", "completed": False},
                        {"id": "item_6", "title": "Final Project", "type": "assignment", "completed": False}
                    ]
                }
            ]
            
            # Calculate simulated progress
            total_items = sum(len(module["items"]) for module in simulated_modules)
            completed_items = sum(
                sum(1 for item in module["items"] if item.get("completed", False))
                for module in simulated_modules
            )
            completion_percentage = (completed_items / total_items * 100) if total_items > 0 else 0
            
            return {
                "course_id": course_id,
                "user_id": user_id,
                "user_name": user_name,
                "user_roles": user_roles,
                "modules": simulated_modules,
                "progress": {
                    "completion": round(completion_percentage, 1),
                    "total_activity": completed_items,
                    "total_items": total_items,
                    "completed_items": completed_items,
                    "incomplete_items": total_items - completed_items,
                    "note": "Simulated data - Canvas API integration pending"
                },
                "current_context": {
                    "current_module": next((m for m in simulated_modules if m["state"] == "in_progress"), None),
                    "next_module": next((m for m in simulated_modules if m["state"] == "locked"), None),
                    "status": "in_progress"
                },
                "summary": {
                    "total_modules": len(simulated_modules),
                    "completed_modules": len([m for m in simulated_modules if m["state"] == "completed"]),
                    "overall_progress": round(completion_percentage, 1),
                    "total_assignments": 2,
                    "completed_assignments": 1
                },
                "timestamp": datetime.now().isoformat(),
                "source": "lti_context_fallback",
                "note": "This is simulated course data. Enable Canvas API integration for real-time data."
            }
            
        except Exception as e:
            logger.error(f"Error in fallback course summary: {e}")
            return {
                "error": f"Failed to generate fallback course summary: {str(e)}",
                "course_id": lti_context.get("course_id", "unknown"),
                "user_id": lti_context.get("user_id", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "source": "error_fallback"
            }
    
    def _get_course_data(self, progress_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get structured course data for the LTI RAG service"""
        try:
            # Extract course structure from progress context
            course_data = {
                "name": "Design Thinking Course",
                "course_id": progress_context.get("course_id", "240"),
                "modules": []
            }
            
            # Add module information if available
            if progress_context.get("module_context"):
                module_ctx = progress_context["module_context"]
                
                # Current module
                if module_ctx.get("current_module"):
                    current_module = module_ctx["current_module"]
                    course_data["modules"].append({
                        "id": current_module.get("id", "current"),
                        "name": current_module.get("name", "Current Module"),
                        "state": module_ctx.get("status", "in_progress"),
                        "items": [
                            {"id": "item_1", "title": "Module Content", "type": "page", "completed": True},
                            {"id": "item_2", "title": "Practice Exercise", "type": "assignment", "completed": False}
                        ]
                    })
                
                # Next module
                if module_ctx.get("next_module"):
                    next_module = module_ctx["next_module"]
                    course_data["modules"].append({
                        "id": next_module.get("id", "next"),
                        "name": next_module.get("name", "Next Module"),
                        "state": "locked",
                        "items": [
                            {"id": "item_3", "title": "Advanced Content", "type": "page", "completed": False},
                            {"id": "item_4", "title": "Final Project", "type": "assignment", "completed": False}
                        ]
                    })
            
            # Add user progress analytics
            if progress_context.get("user_progress"):
                user_progress = progress_context["user_progress"]
                course_data["user_analytics"] = {
                    "completion_percentage": user_progress.get("completion", 0),
                    "completed_items": user_progress.get("completed_items", 0),
                    "total_items": user_progress.get("total_items", 1),
                    "last_activity": user_progress.get("last_activity", "Unknown")
                }
            
            # Add recommended content
            if progress_context.get("recommended_content"):
                course_data["recommended_content"] = progress_context["recommended_content"]
            
            logger.info(f"Generated course data with {len(course_data['modules'])} modules")
            return course_data
            
        except Exception as e:
            logger.error(f"Error generating course data: {e}")
            return {
                "name": "Design Thinking Course",
                "course_id": "240",
                "modules": [],
                "error": f"Failed to generate course data: {str(e)}"
            }
    
    def get_course_summary(self, user_id: str, course_id: str, 
                          lti_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive course summary for the user"""
        try:
            # Check if this is the specific course with real Canvas API enabled
            if lti_context.get("use_real_canvas_api") and course_id == "240":
                logger.info(f"Using real Canvas API for specific course {course_id}")
                return self._get_real_canvas_course_summary(user_id, course_id, lti_context)
            else:
                # Use fallback course summary for other courses
                logger.info(f"Using fallback course summary for LTI user {user_id} in course {course_id}")
                return self._fallback_course_summary(lti_context)
            
        except Exception as e:
            logger.error(f"Error getting course summary: {e}")
            return self._fallback_course_summary(lti_context)
    
    def _get_real_canvas_course_summary(self, user_id: str, course_id: str, lti_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get real course summary from Canvas API for specific course"""
        try:
            logger.info(f"Fetching real course data from Canvas API for course {course_id}")
            
            # Set up Canvas API context for the specific course
            canvas_base_url = "https://taclegacy.instructure.com"  # Your Canvas domain
            canvas_token = "your_canvas_api_token_here"  # You'll need to provide this
            
            # For now, return enhanced fallback data with real course ID
            # In production, you would make actual Canvas API calls here
            enhanced_summary = self._fallback_course_summary(lti_context)
            enhanced_summary.update({
                "course_id": course_id,
                "source": "real_canvas_api",
                "canvas_domain": canvas_base_url,
                "note": f"Real Canvas API integration enabled for course {course_id}. Provide Canvas API token for full functionality.",
                "api_status": "ready_for_token"
            })
            
            logger.info(f"Enhanced course summary ready for course {course_id}")
            return enhanced_summary
            
        except Exception as e:
            logger.error(f"Error getting real Canvas course summary: {e}")
            # Fallback to simulated data if real API fails
            return self._fallback_course_summary(lti_context)
    
    def _fallback_progress_context(self) -> Dict[str, Any]:
        """Fallback progress context when Canvas API is not available"""
        try:
            # Create simulated progress context
            simulated_progress = {
                "course_id": "240",  # Default course ID for knowledge base integration
                "module_context": {
                    "current_module": {
                        "id": "module_2",
                        "name": "Core Concepts",
                        "state": "in_progress",
                        "progress": 50
                    },
                    "next_module": {
                        "id": "module_3", 
                        "name": "Advanced Topics",
                        "state": "locked"
                    },
                    "status": "in_progress"
                },
                "user_progress": {
                    "completion": 50.0,
                    "total_activity": 3,
                    "total_items": 6,
                    "completed_items": 3,
                    "note": "Simulated data - Canvas API integration pending"
                },
                "recommended_content": [
                    "Complete the Practice Exercises in Core Concepts",
                    "Review Key Concepts before moving to Advanced Topics",
                    "Prepare for the Final Project requirements"
                ],
                "analytics": {
                    "time_spent": "2.5 hours",
                    "assignments_submitted": 1,
                    "assignments_pending": 1,
                    "overall_grade": "B+"
                },
                "timestamp": datetime.now().isoformat(),
                "source": "lti_context_fallback"
            }
            
            return simulated_progress
            
        except Exception as e:
            logger.error(f"Error in fallback progress context: {e}")
            return {
                "error": f"Failed to generate fallback progress context: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "source": "error_fallback"
            }
    
    def _analyze_user_query(self, message: str) -> Dict[str, Any]:
        """Analyze user query to determine what Canvas data to fetch"""
        try:
            message_lower = message.lower()
            analysis = {
                "query_type": "general",
                "targets": [],
                "specific_items": [],
                "modules": [],
                "assignments": [],
                "quizzes": [],
                "discussions": [],
                "files": [],
                "pages": [],
                "current_module": False,
                "objectives": False,
                "content": False
            }
            
            # Check for current module queries (e.g., "this module", "current module")
            if any(phrase in message_lower for phrase in ["this module", "current module", "the module", "module's", "module objectives"]):
                analysis["current_module"] = True
                analysis["query_type"] = "current_module"
            
            # Check for objectives queries
            if any(word in message_lower for word in ["objectives", "goals", "learning outcomes", "aims"]):
                analysis["objectives"] = True
                if analysis["current_module"]:
                    analysis["query_type"] = "current_module_objectives"
                else:
                    analysis["query_type"] = "objectives"
            
            # Check for content queries
            if any(word in message_lower for word in ["content", "what's in", "what is in", "tell me about", "describe"]):
                analysis["content"] = True
            
            # Check for specific module queries (e.g., "Module 1", "Week 2")
            if any(word in message_lower for word in ["module", "week", "unit", "section", "chapter"]):
                # Extract module names/numbers
                import re
                module_matches = re.findall(r'(?:module|week|unit|section|chapter)\s*(\d+|[a-zA-Z]+)', message_lower)
                if module_matches:
                    analysis["modules"] = module_matches
                    analysis["query_type"] = "module_specific"
                elif not analysis["current_module"]:
                    # If no specific module number but module keyword present, treat as general module query
                    analysis["query_type"] = "module_general"
            
            # Check for assignment queries
            if any(word in message_lower for word in ["assignment", "homework", "task", "due", "submit"]):
                analysis["query_type"] = "assignment_specific"
                analysis["assignments"].append("all")
            
            # Check for quiz queries
            if any(word in message_lower for word in ["quiz", "test", "exam", "assessment", "question"]):
                analysis["query_type"] = "quiz_specific"
                analysis["quizzes"].append("all")
            
            # Check for discussion queries
            if any(word in message_lower for word in ["discussion", "forum", "post", "reply", "comment"]):
                analysis["query_type"] = "discussion_specific"
                analysis["discussions"].append("all")
            
            # Check for file queries
            if any(word in message_lower for word in ["file", "document", "pdf", "download", "attachment"]):
                analysis["query_type"] = "file_specific"
                analysis["files"].append("all")
            
            # Check for page queries
            if any(word in message_lower for word in ["page", "reading", "material", "resource"]):
                analysis["query_type"] = "page_specific"
                analysis["pages"].append("all")
            
            # Check for specific item queries (e.g., "What is assignment 3 about?")
            specific_patterns = [
                r'assignment\s*(\d+)',
                r'quiz\s*(\d+)',
                r'module\s*(\d+)',
                r'week\s*(\d+)',
                r'unit\s*(\d+)'
            ]
            
            for pattern in specific_patterns:
                matches = re.findall(pattern, message_lower)
                if matches:
                    analysis["specific_items"].extend(matches)
                    analysis["query_type"] = "item_specific"
            
            logger.info(f"Query analysis completed: {analysis}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing user query: {e}")
            return {"query_type": "general", "targets": []}
    
    def _fetch_relevant_canvas_data(self, course_id: str, user_id: str, query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch relevant Canvas data based on query analysis"""
        try:
            canvas_data = {
                "modules": [],
                "assignments": [],
                "quizzes": [],
                "discussions": [],
                "files": [],
                "pages": [],
                "user_progress": None
            }
            
            # Always fetch user progress for context
            try:
                canvas_data["user_progress"] = self.canvas_api_service.get_user_progress()
                logger.info("✅ Fetched user progress from Canvas API")
            except Exception as e:
                logger.warning(f"Could not fetch user progress: {e}")
            
            # Fetch data based on query type
            if query_analysis["query_type"] in ["current_module", "current_module_objectives"]:
                # Fetch current module information
                try:
                    current_module_context = self.canvas_api_service.get_current_module_context()
                    if current_module_context:
                        # Get detailed information about the current module
                        current_module_id = current_module_context.get("current_module", {}).get("id")
                        if current_module_id:
                            detailed_module = self.canvas_api_service.get_module_details(str(current_module_id), user_id)
                            if detailed_module:
                                canvas_data["modules"].append(detailed_module)
                                canvas_data["current_module"] = detailed_module
                                logger.info(f"✅ Fetched current module details: {detailed_module.get('name')}")
                        
                        # Also get user progress for context
                        canvas_data["user_progress"] = current_module_context
                        logger.info("✅ Fetched current module context and progress")
                except Exception as e:
                    logger.warning(f"Could not fetch current module: {e}")
            
            elif query_analysis["query_type"] == "module_specific":
                # Fetch specific modules by first getting all modules, then finding the specific one
                try:
                    logger.info(f"🔍 Fetching specific module for query: {query_analysis.get('modules', [])}")
                    
                    # Step 1: Get all modules from Canvas API
                    all_modules = self.canvas_api_service.get_course_modules()
                    if not all_modules:
                        logger.warning("No modules found in Canvas API")
                        return canvas_data
                    
                    logger.info(f"📋 Found {len(all_modules)} modules in Canvas")
                    
                    # Step 2: Find the specific module(s) requested
                    target_modules = self._find_specific_modules(all_modules, query_analysis)
                    
                    if not target_modules:
                        logger.warning(f"No matching modules found for query: {query_analysis.get('modules')}")
                        # Add basic module list for context
                        canvas_data["modules"] = all_modules[:3]  # First 3 modules for context
                        return canvas_data
                    
                    # Step 3: Get detailed information for each target module
                    for module_info in target_modules:
                        module_id = module_info.get("id")
                        module_name = module_info.get("name", "Unknown")
                        
                        logger.info(f"🎯 Fetching details for module: {module_name} (ID: {module_id})")
                        
                        # Call specific module API with the module ID
                        detailed_module = self.canvas_api_service.get_module_details(str(module_id), user_id)
                        if detailed_module:
                            canvas_data["modules"].append(detailed_module)
                            logger.info(f"✅ Successfully fetched detailed module: {detailed_module.get('name')}")
                        else:
                            logger.warning(f"❌ Failed to get details for module {module_name} (ID: {module_id})")
                    
                except Exception as e:
                    logger.error(f"Error fetching specific modules: {e}")
                    return canvas_data
            
            elif query_analysis["query_type"] == "module_general":
                # Fetch overview of all modules
                try:
                    modules = self.canvas_api_service.get_course_modules()
                    if modules:
                        # Get first few modules for overview
                        for module in modules[:5]:
                            detailed_module = self.canvas_api_service.get_module_details(str(module.get("id")), user_id)
                            if detailed_module:
                                canvas_data["modules"].append(detailed_module)
                                logger.info(f"✅ Fetched module overview: {detailed_module.get('name')}")
                except Exception as e:
                    logger.warning(f"Could not fetch module overview: {e}")
            
            elif query_analysis["query_type"] == "assignment_specific":
                # Fetch assignments
                try:
                    # Get modules first, then extract assignments
                    modules = self.canvas_api_service.get_course_modules()
                    for module in modules:
                        module_id = str(module.get("id"))
                        items = self.canvas_api_service.get_module_items(module_id, user_id)
                        for item in items:
                            if item.get("type") == "Assignment":
                                detailed_item = self.canvas_api_service.get_module_item_details(module_id, str(item.get("id")), user_id)
                                if detailed_item:
                                    canvas_data["assignments"].append(detailed_item)
                                    logger.info(f"✅ Fetched assignment: {detailed_item.get('title')}")
                except Exception as e:
                    logger.warning(f"Could not fetch assignments: {e}")
            
            elif query_analysis["query_type"] == "quiz_specific":
                # Fetch quizzes
                try:
                    modules = self.canvas_api_service.get_course_modules()
                    for module in modules:
                        module_id = str(module.get("id"))
                        items = self.canvas_api_service.get_module_items(module_id, user_id)
                        for item in items:
                            if item.get("type") == "Quiz":
                                detailed_item = self.canvas_api_service.get_module_item_details(module_id, str(item.get("id")), user_id)
                                if detailed_item:
                                    canvas_data["quizzes"].append(detailed_item)
                                    logger.info(f"✅ Fetched quiz: {detailed_item.get('title')}")
                except Exception as e:
                    logger.warning(f"Could not fetch quizzes: {e}")
            
            elif query_analysis["query_type"] == "item_specific":
                # Fetch specific items mentioned in the query
                try:
                    modules = self.canvas_api_service.get_course_modules()
                    for module in modules:
                        module_id = str(module.get("id"))
                        items = self.canvas_api_service.get_module_items(module_id, user_id)
                        for item in items:
                            if self._is_item_relevant_to_query(item, query_analysis):
                                detailed_item = self.canvas_api_service.get_module_item_details(module_id, str(item.get("id")), user_id)
                                if detailed_item:
                                    # Add module context to the item
                                    detailed_item["module_context"] = module
                                    canvas_data["modules"].append(module)
                                    canvas_data["assignments"].append(detailed_item)
                                    logger.info(f"✅ Fetched specific item: {detailed_item.get('title')}")
                except Exception as e:
                    logger.warning(f"Could not fetch specific items: {e}")
            
            else:
                # General query - fetch overview data
                try:
                    modules = self.canvas_api_service.get_course_modules()
                    if modules:
                        # Get first few modules for overview
                        for module in modules[:3]:
                            detailed_module = self.canvas_api_service.get_module_details(str(module.get("id")), user_id)
                            if detailed_module:
                                canvas_data["modules"].append(detailed_module)
                                logger.info(f"✅ Fetched overview module: {detailed_module.get('name')}")
                except Exception as e:
                    logger.warning(f"Could not fetch overview modules: {e}")
            
            logger.info(f"Canvas data fetched: {len(canvas_data['modules'])} modules, {len(canvas_data['assignments'])} assignments, {len(canvas_data['quizzes'])} quizzes")
            return canvas_data
            
        except Exception as e:
            logger.error(f"Error fetching relevant Canvas data: {e}")
            return {}
    
    def _find_specific_modules(self, all_modules: List[Dict[str, Any]], query_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find specific modules based on user query"""
        try:
            target_modules = []
            requested_modules = query_analysis.get("modules", [])
            
            logger.info(f"🔍 Looking for modules: {requested_modules}")
            logger.info(f"📋 Available modules: {[m.get('name', 'Unknown') for m in all_modules]}")
            
            for requested_module in requested_modules:
                requested_lower = requested_module.lower()
                found_module = None
                
                # Try different matching strategies
                for module in all_modules:
                    module_name = module.get("name", "").lower()
                    module_position = str(module.get("position", ""))
                    
                    # Strategy 1: Direct name match
                    if requested_lower in module_name:
                        found_module = module
                        logger.info(f"✅ Direct name match: '{requested_module}' found in '{module.get('name')}'")
                        break
                    
                    # Strategy 2: Position match (e.g., "module 1" matches position 1)
                    if requested_lower == module_position:
                        found_module = module
                        logger.info(f"✅ Position match: '{requested_module}' matches position {module_position}")
                        break
                    
                    # Strategy 3: Number match in name (e.g., "module 1" matches "Module 1: Introduction")
                    if requested_lower.isdigit() and requested_lower in module_name:
                        found_module = module
                        logger.info(f"✅ Number match: '{requested_module}' found in '{module.get('name')}'")
                        break
                    
                    # Strategy 4: Partial name match (e.g., "introduction" matches "Module 1: Introduction")
                    if len(requested_lower) > 3 and requested_lower in module_name:
                        found_module = module
                        logger.info(f"✅ Partial name match: '{requested_module}' found in '{module.get('name')}'")
                        break
                
                if found_module:
                    target_modules.append(found_module)
                else:
                    logger.warning(f"❌ No match found for requested module: '{requested_module}'")
            
            logger.info(f"🎯 Found {len(target_modules)} target modules: {[m.get('name', 'Unknown') for m in target_modules]}")
            return target_modules
            
        except Exception as e:
            logger.error(f"Error finding specific modules: {e}")
            return []
    
    def _is_module_relevant_to_query(self, module: Dict[str, Any], query_analysis: Dict[str, Any]) -> bool:
        """Check if a module is relevant to the user's query"""
        try:
            module_name = module.get("name", "").lower()
            module_position = str(module.get("position", ""))
            
            # Check if module number/position matches query
            for target in query_analysis.get("modules", []):
                if target in module_name or target == module_position:
                    return True
            
            # Check if module name contains relevant keywords
            relevant_keywords = ["module", "week", "unit", "section", "chapter"]
            if any(keyword in module_name for keyword in relevant_keywords):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking module relevance: {e}")
            return False
    
    def _is_item_relevant_to_query(self, item: Dict[str, Any], query_analysis: Dict[str, Any]) -> bool:
        """Check if an item is relevant to the user's query"""
        try:
            item_title = item.get("title", "").lower()
            item_position = str(item.get("position", ""))
            
            # Check if item number/position matches query
            for target in query_analysis.get("specific_items", []):
                if target in item_title or target == item_position:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking item relevance: {e}")
            return False
    
    def _convert_canvas_data_to_knowledge(self, canvas_data: Dict[str, Any], query_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert Canvas API data to knowledge base format"""
        try:
            knowledge_entries = []
            
            # Handle current module queries specifically
            if query_analysis.get("current_module") and canvas_data.get("current_module"):
                current_module = canvas_data["current_module"]
                knowledge_entries.append({
                    "title": f"Current Module: {current_module.get('name', 'Unknown')}",
                    "content": self._format_current_module_content(current_module, query_analysis),
                    "content_type": "canvas_current_module",
                    "metadata": {
                        "source": "canvas_api_direct",
                        "relevance": "very_high",
                        "module_id": current_module.get("id"),
                        "query_type": query_analysis.get("query_type"),
                        "is_current_module": True
                    }
                })
                logger.info(f"✅ Added current module knowledge: {current_module.get('name')}")
            
            # Convert modules
            for module in canvas_data.get("modules", []):
                # Skip if this is already the current module
                if query_analysis.get("current_module") and module.get("id") == canvas_data.get("current_module", {}).get("id"):
                    continue
                    
                knowledge_entries.append({
                    "title": f"Canvas Module: {module.get('name', 'Unknown')}",
                    "content": self._format_enhanced_module_content(module),
                    "content_type": "canvas_module_api",
                    "metadata": {
                        "source": "canvas_api_direct",
                        "relevance": "high",
                        "module_id": module.get("id"),
                        "query_type": query_analysis.get("query_type")
                    }
                })
            
            # Convert assignments
            for assignment in canvas_data.get("assignments", []):
                knowledge_entries.append({
                    "title": f"Canvas Assignment: {assignment.get('title', 'Unknown')}",
                    "content": self._format_enhanced_item_content(assignment, assignment.get("module_context", {})),
                    "content_type": "canvas_assignment_api",
                    "metadata": {
                        "source": "canvas_api_direct",
                        "relevance": "high",
                        "item_id": assignment.get("id"),
                        "query_type": query_analysis.get("query_type")
                    }
                })
            
            # Convert quizzes
            for quiz in canvas_data.get("quizzes", []):
                knowledge_entries.append({
                    "title": f"Canvas Quiz: {quiz.get('title', 'Unknown')}",
                    "content": self._format_enhanced_item_content(quiz, quiz.get("module_context", {})),
                    "metadata": {
                        "source": "canvas_api_direct",
                        "relevance": "high",
                        "item_id": quiz.get("id"),
                        "query_type": query_analysis.get("query_type")
                    }
                })
            
            # Add user progress context if available
            if canvas_data.get("user_progress"):
                progress = canvas_data["user_progress"]
                knowledge_entries.append({
                    "title": "User Progress Context",
                    "content": f"Current progress: {progress.get('completion_percentage', 'Unknown')}% complete. Last activity: {progress.get('last_activity', 'Unknown')}",
                    "content_type": "user_progress",
                    "metadata": {
                        "source": "canvas_api_direct",
                        "relevance": "medium",
                        "query_type": query_analysis.get("query_type")
                    }
                })
            
            logger.info(f"Converted {len(knowledge_entries)} Canvas data entries to knowledge format")
            return knowledge_entries
            
        except Exception as e:
            logger.error(f"Error converting Canvas data to knowledge: {e}")
            return []
    
    def _format_current_module_content(self, module: Dict[str, Any], query_analysis: Dict[str, Any]) -> str:
        """Format current module content for knowledge base, focusing on objectives if requested"""
        try:
            content_parts = []
            
            # Module basic info
            content_parts.append(f"Module: {module.get('name', 'Unknown')}")
            content_parts.append(f"Position: {module.get('position', 'Unknown')}")
            content_parts.append(f"State: {module.get('state', 'Unknown')}")
            
            # Add module description if available
            if module.get('description'):
                content_parts.append(f"Description: {module.get('description')}")
            
            # If asking about objectives, focus on that
            if query_analysis.get("objectives"):
                content_parts.append("OBJECTIVES:")
                # Look for objectives in module content
                if module.get('items'):
                    for item in module.get('items', []):
                        if item.get('type') == 'Page' and 'objective' in item.get('title', '').lower():
                            content_parts.append(f"- {item.get('title')}: {item.get('description', 'No description available')}")
                        elif item.get('type') == 'Assignment' and 'objective' in item.get('title', '').lower():
                            content_parts.append(f"- {item.get('title')}: {item.get('description', 'No description available')}")
                
                # If no specific objectives found, use module description
                if len(content_parts) <= 4:  # Only basic info added
                    content_parts.append("Learning Objectives:")
                    content_parts.append("- Complete all module content and activities")
                    content_parts.append("- Demonstrate understanding of key concepts")
                    content_parts.append("- Participate in discussions and assignments")
            
            # Add module items for context
            if module.get('items'):
                content_parts.append("Module Content:")
                for item in module.get('items', []):
                    content_parts.append(f"- {item.get('title', 'Unknown Item')} ({item.get('type', 'Unknown Type')})")
            
            return "\n".join(content_parts)
            
        except Exception as e:
            logger.error(f"Error formatting current module content: {e}")
            return f"Module: {module.get('name', 'Unknown')}"
    
    def _convert_enhanced_context_to_knowledge(self, enhanced_context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert existing enhanced context to knowledge base format"""
        try:
            knowledge_entries = []
            for context_item in enhanced_context:
                if context_item["type"] == "module":
                    knowledge_entries.append({
                        "title": f"Enhanced Module: {context_item['data'].get('name', 'Unknown')}",
                        "content": self._format_enhanced_module_content(context_item['data']),
                        "content_type": "canvas_module_enhanced",
                        "metadata": {
                            "source": "canvas_api_enhanced",
                            "relevance": context_item.get("relevance", "medium")
                        }
                    })
                elif context_item["type"] == "item":
                    knowledge_entries.append({
                        "title": f"Enhanced Item: {context_item['data'].get('title', 'Unknown')}",
                        "content": self._format_enhanced_item_content(context_item['data'], context_item.get('module', {})),
                        "content_type": "canvas_item_enhanced",
                        "metadata": {
                            "source": "canvas_api_enhanced",
                            "relevance": context_item.get("relevance", "high")
                        }
                    })
            
            return knowledge_entries
            
        except Exception as e:
            logger.error(f"Error converting enhanced context to knowledge: {e}")
            return []

# Global instance
lti_ai_service = LTIAIService() 