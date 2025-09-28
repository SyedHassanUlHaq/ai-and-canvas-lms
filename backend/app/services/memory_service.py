"""
Enhanced Memory Service for Iframe Widget Flow
Handles conversation memory and quiz state management with database storage
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
import os

from app.core.config import settings
from app.models.conversation_memory import ConversationMemory, Base

logger = logging.getLogger(__name__)


class MemoryService:
    """Enhanced memory service with database storage for conversation memory and quiz state"""
    
    def __init__(self):
        """Initialize memory service with database connection"""
        try:
            from app.core.config import settings
            
            # Build database URL
            db_url = f"postgresql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
            
            # Only create engine if we're not in production Cloud Run (no database)
            if os.getenv("ENVIRONMENT") == "production":
                logger.warning("Running in production Cloud Run without database - using fallback memory")
                self.engine = None
            else:
                # self.engine = create_engine(db_url)
                # # Create tables if they don't exist
                # Base.metadata.create_all(bind=self.engine)
                logger.info("Memory service initialized with database connection")
                
        except Exception as e:
            logger.warning(f"Failed to initialize database connection: {e}")
            logger.info("Memory service will use fallback memory storage")
            self.engine = None
    
    def get_session(self) -> Session:
        """Get database session"""
        if not self.engine:
            raise Exception("Database engine not initialized")
        return Session(self.engine)
    
    def get_conversation_memory(self, user_id: str, course_id: Optional[str] = None, module_item_id: Optional[str] = None) -> Any:
        """Get conversation memory with quiz state from database"""
        try:
            if not self.engine:
                return EnhancedMemory("fallback", [], None)
            
            session = self.get_session()
            
            # Get conversation history
            query = session.query(ConversationMemory).filter(
                ConversationMemory.user_id == user_id,
                ConversationMemory.course_id == course_id
            )
            
            if module_item_id:
                query = query.filter(ConversationMemory.module_item_id == module_item_id)
            
            conversations = query.order_by(ConversationMemory.timestamp.desc()).limit(20).all()
            
            # Convert to list format
            conversation_list = []
            for conv in conversations:
                conversation_list.append({
                    "timestamp": conv.timestamp.isoformat(),
                    "user_message": conv.message if conv.message_type == "user" else "",
                    "ai_response": conv.response if conv.message_type == "ai" else conv.message,
                    "course_id": conv.course_id,
                    "module_item_id": conv.module_item_id,
                    "context_used": json.loads(conv.context_used) if conv.context_used else []
                })
            
            # Get quiz state
            # quiz_state = session.query(QuizState).filter(
            #     QuizState.user_id == user_id,
            #     QuizState.course_id == course_id
            # ).first()
            
            session.close()
            
            return EnhancedMemory(
                f"{user_id}_{course_id}", 
                conversation_list,
                # quiz_state
            )
            
        except Exception as e:
            logger.error(f"Error getting conversation memory: {e}")
            return EnhancedMemory("fallback", [], None)
    
    def store_lti_session(self, session_token: str, session_data: Dict[str, Any]) -> bool:
        """Store LTI session data"""
        try:
            # For now, store in memory (in production, use Redis or database)
            if not hasattr(self, '_lti_sessions'):
                self._lti_sessions = {}
            
            self._lti_sessions[session_token] = session_data
            logger.info(f"LTI session stored: {session_token}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing LTI session: {e}")
            return False
    
    def get_lti_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get LTI session data"""
        try:
            if not hasattr(self, '_lti_sessions'):
                return None
            
            session_data = self._lti_sessions.get(session_token)
            if session_data:
                # Check if session is expired
                expires_at = session_data.get('expires_at')
                if expires_at:
                    from datetime import datetime
                    if datetime.fromisoformat(expires_at) < datetime.utcnow():
                        # Session expired, remove it
                        del self._lti_sessions[session_token]
                        return None
                
                return session_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting LTI session: {e}")
            return None
    
    def delete_lti_session(self, session_token: str) -> bool:
        """Delete LTI session data"""
        try:
            if not hasattr(self, '_lti_sessions'):
                return True
            
            if session_token in self._lti_sessions:
                del self._lti_sessions[session_token]
                logger.info(f"LTI session deleted: {session_token}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting LTI session: {e}")
            return False
    
    def store_lti_storage(self, key: str, value: str) -> bool:
        """Store data in LTI platform storage"""
        try:
            if not hasattr(self, '_lti_storage'):
                self._lti_storage = {}
            
            self._lti_storage[key] = value
            logger.info(f"LTI storage data stored: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing LTI storage data: {e}")
            return False
    
    def get_lti_storage(self, key: str) -> Optional[str]:
        """Get data from LTI platform storage"""
        try:
            if not hasattr(self, '_lti_storage'):
                return None
            
            value = self._lti_storage.get(key)
            if value:
                logger.info(f"LTI storage data retrieved: {key}")
            
            return value
            
        except Exception as e:
            logger.error(f"Error getting LTI storage data: {e}")
            return None
    
    def delete_lti_storage(self, key: str) -> bool:
        """Delete data from LTI platform storage"""
        try:
            if not hasattr(self, '_lti_storage'):
                return True
            
            if key in self._lti_storage:
                del self._lti_storage[key]
                logger.info(f"LTI storage data deleted: {key}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting LTI storage data: {e}")
            return False
    
    def add_to_memory(self, user_id: str, course_id: str, message: str, response: str, 
                      module_item_id: Optional[str] = None, context_used: Optional[List[Dict]] = None) -> bool:
        """Add conversation to memory in database"""
        try:
            if not self.engine:
                return False
            
            session = self.get_session()
            
            # Add user message
            user_memory = ConversationMemory(
                user_id=user_id,
                course_id=course_id,
                module_item_id=module_item_id,
                message=message,
                response="",  # User messages don't have AI responses
                message_type="user",
                context_used=json.dumps(context_used) if context_used else None
            )
            session.add(user_memory)
            
            # Add AI response
            ai_memory = ConversationMemory(
                user_id=user_id,
                course_id=course_id,
                module_item_id=module_item_id,
                message="",  # AI responses don't have user messages
                response=response,
                message_type="ai",
                context_used=json.dumps(context_used) if context_used else None
            )
            session.add(ai_memory)
            
            session.commit()
            session.close()
            
            logger.info(f"Added conversation to database memory for {user_id}_{course_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding to memory: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()
            return False


    def get_conversation_summary(self, user_id: str, course_id: str, module_item_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of conversation history from database"""
        try:
            if not self.engine:
                return {"has_history": False}
            
            session = self.get_session()
            
            # Build query
            query = session.query(ConversationMemory).filter(
                ConversationMemory.user_id == user_id,
                ConversationMemory.course_id == course_id
            )
            
            if module_item_id:
                query = query.filter(ConversationMemory.module_item_id == module_item_id)
            
            conversations = query.all()
            
            if not conversations:
                session.close()
                return {"has_history": False}
            
            # Analyze conversation patterns
            total_messages = len(conversations)
            total_user_chars = sum(len(conv.message) for conv in conversations if conv.message_type == "user")
            total_ai_chars = sum(len(conv.response) for conv in conversations if conv.message_type == "ai")
            
            # Find common topics from user messages
            common_words = {}
            for conv in conversations:
                if conv.message_type == "user":
                    message_words = conv.message.lower().split()
                    for word in message_words:
                        if len(word) > 3:  # Only count words longer than 3 characters
                            common_words[word] = common_words.get(word, 0) + 1
            
            # Get top 5 most common words
            top_words = sorted(common_words.items(), key=lambda x: x[1], reverse=True)[:5]
            
            session.close()
            
            return {
                "has_history": True,
                "total_messages": total_messages,
                "total_user_chars": total_user_chars,
                "total_ai_chars": total_ai_chars,
                "common_topics": top_words,
                "module_item_id": module_item_id
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation summary: {e}")
            return {"has_history": False, "error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        """Check memory service health"""
        try:
            if not self.engine:
                return {"status": "error", "message": "Database engine not initialized"}
            
            # Test database connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            return {"status": "ok", "message": "Database connection successful"}
            
        except Exception as e:
            logger.error(f"Memory service health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def cleanup_old_conversations(self, days_old: int = 30) -> int:
        """Clean up conversations older than specified days"""
        try:
            if not self.engine:
                return 0
            
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            session = self.get_session()
            
            # Delete old conversations
            deleted_count = session.query(ConversationMemory).filter(
                ConversationMemory.timestamp < cutoff_date
            ).delete()
            
            # Delete old quiz states
            # quiz_deleted_count = session.query(QuizState).filter(
            #     QuizState.last_updated < cutoff_date
            # ).delete()
            
            session.commit()
            session.close()
            
            # logger.info(f"Cleaned up {deleted_count} old conversations and {quiz_deleted_count} old quiz states older than {days_old} days")
            # return deleted_count + quiz_deleted_count
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old conversations: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()
            return 0

    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get statistics about conversation storage"""
        try:
            if not self.engine:
                return {}
            
            session = self.get_session()
            
            # Total conversations
            total_conversations = session.query(ConversationMemory).count()
            
            # Conversations by age
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            
            last_7_days = session.query(ConversationMemory).filter(
                ConversationMemory.timestamp >= now - timedelta(days=7)
            ).count()
            
            last_30_days = session.query(ConversationMemory).filter(
                ConversationMemory.timestamp >= now - timedelta(days=30)
            ).count()
            
            # Oldest conversation
            oldest = session.query(ConversationMemory).order_by(ConversationMemory.timestamp.asc()).first()
            oldest_date = oldest.timestamp if oldest else None
            
            # Quiz states
            # total_quiz_states = session.query(QuizState).count()
            
            session.close()
            
            return {
                "total_conversations": total_conversations,
                "last_7_days": last_7_days,
                "last_30_days": last_30_days,
                "oldest_conversation": oldest_date.isoformat() if oldest_date else None,
                # "total_quiz_states": total_quiz_states
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation stats: {e}")
            return {}


class EnhancedMemory:
    """Enhanced memory object with database-backed storage"""
    
    def __init__(self, memory_key: str, conversations: List[Dict]):
        self.memory_key = memory_key
        self.conversations = conversations
        # self.quiz_state = quiz_state
    
    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history"""
        return self.conversations


# Global instance
memory_service = MemoryService() 