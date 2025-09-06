"""
Enhanced AI Service for Iframe Widget Flow
Handles AI interactions and quiz functionality
"""

import logging
import os
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

# Quiz service removed

logger = logging.getLogger(__name__)


class AIService:
    """Enhanced AI service with quiz functionality"""
    
    def __init__(self):
        """Initialize AI service"""
        logger.info("AI service initialized with quiz functionality")
        
        # Basic configuration
        self.default_language = "en"
        self.supported_languages = ["en", "id"]
        
        # Quiz functionality removed
    
    def generate_response(self, message: str, context_docs: List[Dict[str, Any]] = None, 
                         memory: Any = None, language: str = "en", course_id: str = None) -> Dict[str, Any]:
        """Generate AI response with quiz support"""
        try:
            logger.info(f"Generating AI response for message: {message[:50]}...")
            logger.info(f"🔍 Message: '{message}', Language: {language}")
            
            # Regular AI response (quiz functionality removed)
            return self._generate_regular_response(message, context_docs, memory, language, course_id)
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return {
                "reply": f"Sorry, I encountered an error: {str(e)}",
                "context_used": [],
                "confidence": "low",
                "total_context_docs": 0,
                "error": str(e)
            }
    

    
    def _generate_regular_response(self, message: str, context_docs: List[Dict[str, Any]], 
                                 memory: Any, language: str, course_id: str = None) -> Dict[str, Any]:
        """Generate context-aware AI response using conversation memory and course content"""
        try:
            # Get conversation history for context
            conversation_history = []
            if memory and hasattr(memory, 'get_conversation_history'):
                conversation_history = memory.get_conversation_history()
            
            # Use the context_docs passed from main.py (these are already filtered for the specific module item)
            relevant_docs = context_docs or []
            
            logger.info(f"🔍 Using {len(relevant_docs)} context documents passed from main.py")
            if relevant_docs:
                for i, doc in enumerate(relevant_docs):
                    logger.info(f"   Doc {i+1}: {doc.get('title', 'Unknown')} (Type: {doc.get('content_type', 'Unknown')}, Length: {len(doc.get('content', ''))})")
            
            # Build context-aware response
            if relevant_docs:
                # Found relevant content
                response = self._build_contextual_response(message, relevant_docs, conversation_history, language)
                confidence = "high"
            elif conversation_history:
                # No relevant content but have conversation history
                response = self._build_conversation_aware_response(message, conversation_history, language)
                confidence = "medium"
            else:
                # No context or history
                response = self._build_general_response(message, language)
                confidence = "low"
            
            return {
                "reply": response,
                "context_used": relevant_docs or [],
                "confidence": confidence,
                "total_context_docs": len(relevant_docs) if relevant_docs else 0,
                "insights": {
                    "language_detected": language,
                    "response_type": "regular",
                    "context_used_count": len(relevant_docs) if relevant_docs else 0,
                    "conversation_history_length": len(conversation_history),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating regular response: {e}")
            return self._generate_error_response(str(e), language)
    
    def _build_contextual_response(self, message: str, relevant_docs: List[Dict[str, Any]], 
                                 conversation_history: List[Dict[str, Any]], language: str) -> str:
        """Build response using relevant course content"""
        try:
            if language == "id":
                response = f"Berdasarkan materi kursus, saya dapat membantu Anda dengan pertanyaan tentang '{message}'. 🎓\n\n"
                
                # Add relevant content information
                for i, doc in enumerate(relevant_docs[:2]):  # Show top 2 relevant items
                    doc_type = self._get_document_type_display(doc.get("content_type", ""), language)
                    response += f"**{doc_type}:** {doc.get('title', 'Unknown')}\n"
                    content_preview = doc.get('content', '')[:150]
                    if len(content_preview) > 150:
                        content_preview += "..."
                    response += f"{content_preview}\n\n"
                
                response += "Apakah ada aspek spesifik yang ingin Anda ketahui lebih lanjut?"
                
            else:
                response = f"Based on the course materials, I can help you with your question about '{message}'. 🎓\n\n"
                
                # Add relevant content information
                for i, doc in enumerate(relevant_docs[:2]):  # Show top 2 relevant items
                    doc_type = self._get_document_type_display(doc.get("content_type", ""), language)
                    response += f"**{doc_type}:** {doc.get('title', 'Unknown')}\n"
                    content_preview = doc.get('content', '')[:150]
                    if len(content_preview) > 150:
                        content_preview += "..."
                    response += f"{content_preview}\n\n"
                
                response += "Is there a specific aspect you'd like to know more about?"
            
            return response
            
        except Exception as e:
            logger.error(f"Error building contextual response: {e}")
            return self._build_general_response(message, language)
    
    def _build_conversation_aware_response(self, message: str, conversation_history: List[Dict[str, Any]], 
                                         language: str) -> str:
        """Build response using conversation history for context"""
        try:
            # Look for related topics in conversation history
            related_topics = []
            message_lower = message.lower()
            
            # Log the conversation analysis limit change
            analysis_limit = 10
            logger.info(f"🔍 Analyzing last {analysis_limit} conversations for topic relevance (increased from 5)")
            
            for conv in conversation_history[-analysis_limit:]:  # Check last 10 conversations (increased from 5)
                if 'ai_response' in conv:
                    response_text = conv['ai_response'].lower()
                    if any(word in response_text for word in message_lower.split()):
                        related_topics.append(conv)
            
            logger.info(f"🔍 Found {len(related_topics)} related topics in last {analysis_limit} conversations")
            
            if related_topics:
                if language == "id":
                    response = f"Saya melihat Anda telah membahas topik serupa sebelumnya. Berdasarkan percakapan kita, "
                    response += f"'{message}' terkait dengan materi yang sudah kita bahas. "
                    response += "Apakah Anda ingin saya menjelaskan lebih detail atau ada aspek baru yang ingin Anda ketahui?"
                else:
                    response = f"I notice we've discussed related topics before. Based on our conversation, "
                    response += f"'{message}' relates to material we've covered. "
                    response += "Would you like me to explain in more detail or is there a new aspect you'd like to explore?"
            else:
                response = self._build_general_response(message, language)
            
            return response
            
        except Exception as e:
            logger.error(f"Error building conversation-aware response: {e}")
            return self._build_general_response(message, language)
    
    def _build_general_response(self, message: str, language: str) -> str:
        """Build general response when no specific context is available"""
        try:
            if language == "id":
                response = f"Saya memahami pertanyaan Anda tentang '{message}'. "
                response += "Meskipun saya tidak memiliki akses langsung ke materi kursus saat ini, "
                response += "saya dapat membantu Anda dengan konsep umum dan dapat memberikan kuis untuk menguji pengetahuan Anda. "
                response += "Apakah Anda ingin saya memberikan kuis atau ada hal lain yang bisa saya bantu?"
            else:
                response = f"I understand your question about '{message}'. "
                response += "While I don't have direct access to course materials right now, "
                response += "I can help you with general concepts and can give you a quiz to test your knowledge. "
                response += "Would you like me to give you a quiz or is there something else I can help with?"
            
            return response
            
        except Exception as e:
            logger.error(f"Error building general response: {e}")
            if language == "id":
                return f"Maaf, saya mengalami kesalahan dalam memproses pertanyaan Anda. Silakan coba lagi."
            else:
                return f"Sorry, I encountered an error processing your question. Please try again."
    
    def _get_document_type_display(self, doc_type: str, language: str) -> str:
        """Get display text for document type"""
        try:
            if language == "id":
                type_map = {
                    "course_info": "Informasi Kursus",
                    "module": "Modul",
                    "module_item": "Item Modul",
                    "page": "Halaman",
                    "assignment": "Tugas"
                }
            else:
                type_map = {
                    "course_info": "Course Information",
                    "module": "Module",
                    "module_item": "Module Item",
                    "page": "Page",
                    "assignment": "Assignment"
                }
            
            return type_map.get(doc_type, doc_type)
            
        except Exception as e:
            logger.error(f"Error getting document type display: {e}")
            return doc_type
    
    def _generate_error_response(self, error: str, language: str) -> Dict[str, Any]:
        """Generate error response"""
        try:
            if language == "id":
                reply = f"Maaf, terjadi kesalahan: {error}. Silakan coba lagi."
            else:
                reply = f"Sorry, an error occurred: {error}. Please try again."
            
            return {
                "reply": reply,
                "context_used": [],
                "confidence": "low",
                "total_context_docs": 0,
                "insights": {
                    "language_detected": language,
                    "response_type": "error",
                    "error": error,
                    "timestamp": datetime.now().isoformat()
                },
                "error": error
            }
            
        except Exception as e:
            logger.error(f"Error generating error response: {e}")
            return {
                "reply": f"Sorry, I encountered an error: {str(e)}",
                "context_used": [],
                "confidence": "low",
                "total_context_docs": 0,
                "insights": {
                    "language_detected": language,
                    "response_type": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                },
                "error": str(e)
            }
    
    def detect_user_language(self, message: str) -> str:
        """Detect user's language preference from message"""
        try:
            # Simple language detection
            indonesian_indicators = ['apa', 'bagaimana', 'mengapa', 'kapan', 'dimana', 'siapa', 'tolong', 'terima kasih']
            message_lower = message.lower()
            
            for indicator in indonesian_indicators:
                if indicator in message_lower:
                    return "id"
            
            return "en"
            
        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return "en"


# Global instance
ai_service = AIService() 