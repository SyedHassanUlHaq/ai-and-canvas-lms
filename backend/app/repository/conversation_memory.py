from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, func, exists
from typing import Optional, List
import json
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from app.schemas.conversation_summary import *
from app.models.conversation_memory import ConversationMemory
import random
import string

class ConversationMemoryRepository:
    def __init__(self, session: AsyncSession):
        self.db = session
    



from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import json

class ConversationMemoryRawRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new conversation memory using raw SQL"""
        sql = text("""
            INSERT INTO conversations 
            (user_id, course_id, module_item_id, message, message_from, session_id, summary, embedding, evaluation, quiz_session_id, quiz_active, current_language)
            VALUES (:user_id, :course_id, :module_item_id, :message, :message_from, :session_id, :summary, :embedding, :evaluation, :quiz_session_id, :quiz_active, :current_language)
            RETURNING *
        """)

        
        params = {
            'user_id': memory_data['user_id'],
            'course_id': memory_data['course_id'],
            'module_item_id': memory_data.get('module_item_id'),
            'message': memory_data['message'],
            'message_from': memory_data.get('message_from', 'user'),
            'session_id': memory_data['session_id'],
            'summary': memory_data['summary'],
            'embedding': memory_data['embedding'],
            'evaluation': memory_data['evaluation'],
            'quiz_session_id': memory_data['quiz_session_id'],
            'quiz_active': memory_data['quiz_active'],
            'current_language': memory_data['current_language']
            # 'context_used': json.dumps(memory_data.get('context_used')) if memory_data.get('context_used') else None
        }
        
        result = await self.session.execute(sql, params)
        await self.session.commit()
        return dict(result.mappings().first())

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a user record by user_id and return as dictionary

        Args:
            user_id: The user ID to look up

        Returns:
            User record as dictionary if found, None otherwise
        """
        sql = text("""
            SELECT * FROM conversations 
            WHERE user_id = :user_id 
            ORDER BY id DESC 
            LIMIT 1
        """)

        result = await self.session.execute(sql, {"user_id": user_id})
        row = result.mappings().first()
        return dict(row) if row else None
    
    async def get_by_user_id(
        self, 
        user_id: str, 
        get_most_recent: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get conversation memories by user ID using raw SQL"""
        if get_most_recent:
            sql = text("""
                SELECT * FROM conversations 
                WHERE user_id = :user_id 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            params = {'user_id': user_id}
        else:
            sql = text("""
                SELECT * FROM conversations 
                WHERE user_id = :user_id 
                ORDER BY timestamp DESC 
                LIMIT :limit OFFSET :offset
            """)
            params = {'user_id': user_id, 'limit': limit, 'offset': offset}
        
        result = await self.session.execute(sql, params)
        return [dict(row) for row in result.mappings().all()]
    
    async def get_by_session_id(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all conversation memories by session ID using raw SQL"""
        sql = text("""
            SELECT * FROM conversations 
            WHERE session_id = :session_id 
            ORDER BY timestamp ASC 
            LIMIT :limit OFFSET :offset
        """)
        
        result = await self.session.execute(sql, {
            'session_id': session_id,
            'limit': limit,
            'offset': offset
        })
        return [dict(row) for row in result.mappings().all()]
    
    async def format_conversations_for_chatbot(
        self,
        session_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Format conversations for chatbot using raw SQL"""
        sql = text("""
            SELECT 
                CASE 
                    WHEN message_from IN ('user', 'human') THEN 'user'
                    ELSE 'ai'
                END as from_field,
                message
            FROM conversations 
            WHERE session_id = :session_id 
            ORDER BY timestamp ASC 
            LIMIT :limit
        """)
        
        result = await self.session.execute(sql, {
            'session_id': session_id,
            'limit': limit
        })
        return [dict(row) for row in result.mappings().all()]


    def generate_random_string(self, length: int = 20) -> str:
        """Generate a random string of specified length"""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))
    
    async def user_exists(self, user_id: str) -> bool:
        """Check if a user exists in the database using raw SQL"""
        sql = text("""
            SELECT EXISTS(
                SELECT 1 FROM conversations 
                WHERE user_id = :user_id
            ) as user_exists
        """)
        
        result = await self.session.execute(sql, {'user_id': user_id})
        return result.scalar()
    
    async def get_most_recent_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent message for a user using raw SQL"""
        sql = text("""
            SELECT * FROM conversations 
            WHERE user_id = :user_id 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        result = await self.session.execute(sql, {'user_id': user_id})
        row = result.mappings().first()
        return dict(row) if row else None
    
    async def create_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new conversation memory using raw SQL"""
        sql = text("""
            INSERT INTO conversations 
            (user_id, course_id, message, message_from, session_id)
            VALUES (:user_id, :course_id, :message, :message_from, :session_id)
            RETURNING *
        """)
        
        result = await self.session.execute(sql, memory_data)
        await self.session.commit()
        row = result.mappings().first()
        return dict(row) if row else None
    
    async def ensure_user_exists_with_welcome_message(
        self,
        user_context: Dict[str, Any],
        welcome_message: str = "Welcome! How can I help you today?",
        message_from: str = "assistant"
    ) -> Tuple[bool, Dict[str, Any]]:

        user_id = user_context["user_id"]
        
        # Check if user exists
        user_exists = await self.user_exists(user_id)
        
        if user_exists:
            # User exists, get their most recent message
            recent_memory = await self.get_most_recent_by_user_id(user_id)
            return False, recent_memory
        
        # User doesn't exist, create welcome message
        # Generate a session ID if not provided in context
        session_id = self.generate_random_string(15)
        
        # Create the welcome memory
        memory_data = {
            'user_id': user_id,
            'course_id': user_context["course_id"],
            # 'module_item_id': user_context.get("module_item_id"),
            'message': welcome_message,
            'message_from': message_from,
            'session_id': session_id,
            'summary': 'AI Tutor Offered Help',
            'embedding': None
            # 'context_used': json.dumps(context_data)
        }
        
        created_memory = await self.create_memory(memory_data)
        return True, created_memory

    async def create_new_session_with_welcome(
        self,
        user_id: str,
        course_id: str = None,
        welcome_message: str = "Welcome! How can I help you today?",
        message_from: str = "assistant"
    ) -> Dict[str, Any]:

        # Generate a new session ID
        session_id = self.generate_random_string(15)
        
        # Create the welcome memory
        memory_data = {
            'user_id': user_id,
            'course_id': course_id,
            'message': welcome_message,
            'message_from': message_from,
            'session_id': session_id,
            'summary': 'New session started with welcome message',
            'embedding': None
        }
        
        sql = text("""
            INSERT INTO conversations 
            (user_id, course_id, message, message_from, session_id, summary, embedding)
            VALUES (:user_id, :course_id, :message, :message_from, :session_id, :summary, :embedding)
            RETURNING *
        """)
        
        try:
            result = await self.session.execute(sql, memory_data)
            await self.session.commit()
            row = result.mappings().first()
            
            if row:
                return dict(row)
            else:
                raise Exception("Failed to create new session - no record returned")
                
        except Exception as e:
            await self.session.rollback()
            raise Exception(f"Failed to create new session for user {user_id}: {str(e)}")


    async def update_latest_summary(self, user_id: str, new_summary: str) -> Dict[str, Any]:
        sql = text("""
            UPDATE conversations 
            SET summary = :new_summary
            WHERE id = (
                SELECT id 
                FROM conversations 
                WHERE user_id = :user_id 
                ORDER BY timestamp DESC 
                LIMIT 1
            )
            RETURNING *
        """)
        
        params = {
            'user_id': user_id,
            'new_summary': new_summary
        }
        
        try:
            result = await self.session.execute(sql, params)
            await self.session.commit()
            updated_record = result.mappings().first()
            
            if updated_record:
                return dict(updated_record)
            else:
                raise ValueError(f"No conversation records found for user_id: {user_id}")
                
        except Exception as e:
            await self.session.rollback()
            raise Exception(f"Failed to update summary for user {user_id}: {str(e)}")

    
    async def get_latest_summary(self, user_id: str) -> Optional[str]:
        sql = text("""
            SELECT summary 
            FROM conversations 
            WHERE user_id = :user_id 
            AND summary IS NOT NULL
            AND summary != ''
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        params = {
            'user_id': user_id
        }
        
        result = await self.session.execute(sql, params)
        row = result.mappings().first()
        
        if row:
            return row['summary']
        return None

    async def find_similar_conversations(self, user_id: str, embedding: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find the top 5 most similar conversation records for a user based on embedding similarity.
        
        Args:
            user_id: The ID of the user to search conversations for
            embedding: The embedding string to compare against
            limit: Number of similar records to return (default: 5)
        
        Returns:
            List of dictionaries containing similar conversation records
        """
        sql = text("""
            SELECT *, 
                   (embedding <=> :embedding) as similarity_score
            FROM conversations 
            WHERE user_id = :user_id
            AND embedding IS NOT NULL
            ORDER BY embedding <=> :embedding
            LIMIT :limit
        """)
        
        params = {
            'user_id': user_id,
            'embedding': embedding,
            'limit': limit
        }
        
        result = await self.session.execute(sql, params)
        rows = result.mappings().all()
        
        return [dict(row) for row in rows] if rows else []


    async def update_user_evaluation_and_quiz_session(
        self, 
        user_id: str, 
        evaluation: str, 
        quiz_session_id: int,
        quiz_active: bool = False  # Add quiz_active parameter
    ) -> Optional[Dict[str, Any]]:
        """Update evaluation, quiz_session_id, and quiz_active for the most recent conversation of a user"""
        sql = text("""
            UPDATE conversations 
            SET evaluation = :evaluation, 
                quiz_session_id = :quiz_session_id,
                quiz_active = :quiz_active
            WHERE id = (
                SELECT id FROM conversations 
                WHERE user_id = :user_id 
                ORDER BY timestamp DESC 
                LIMIT 1
            )
            RETURNING *
        """)
        
        params = {
            'user_id': user_id,
            'evaluation': evaluation,
            'quiz_session_id': quiz_session_id,
            'quiz_active': quiz_active
        }
        
        result = await self.session.execute(sql, params)
        await self.session.commit()
        row = result.mappings().first()
        return dict(row) if row else None
    
    async def update_quiz_active_status(
        self, 
        user_id: str, 
        quiz_active: bool
    ) -> Optional[Dict[str, Any]]:
        """Update only the quiz_active status for the most recent conversation of a user"""
        sql = text("""
            UPDATE conversations 
            SET quiz_active = :quiz_active
            WHERE id = (
                SELECT id FROM conversations 
                WHERE user_id = :user_id 
                ORDER BY timestamp DESC 
                LIMIT 1
            )
            RETURNING *
        """)
        
        params = {
            'user_id': user_id,
            'quiz_active': quiz_active
        }
        
        result = await self.session.execute(sql, params)
        await self.session.commit()
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_latest_quiz_session_id(self, session_id: str) -> Optional[str]:
        """Return the quiz_session_id of the latest record (by timestamp)
        where there are more than 5 records with that quiz_session_id.
        """
        sql = text("""
            SELECT c.quiz_session_id
            FROM conversations c
            WHERE c.session_id = :session_id
              AND c.evaluation = 'passed'
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        result = await self.session.execute(sql, {"session_id": session_id})
        row = result.first()
        return row[0] if row else None