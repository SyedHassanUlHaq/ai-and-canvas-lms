from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, func, exists
from typing import Optional, List
import json
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from app.schemas.conversation_summary import *
from app.models.conversations_rce import ConversationMemory_rce
import random
import string

class ConversationMemoryRepository:
    def __init__(self, session: AsyncSession):
        self.db = session
    
    # async def create(self, memory_data: ConversationMemoryCreate) -> ConversationMemory:
    #     """Create a new conversation memory"""
    #     # Convert context_used dict to JSON string if provided
    #     db_memory = ConversationMemory(
    #         user_id=memory_data.user_id,
    #         course_id=memory_data.course_id,
    #         module_item_id=memory_data.module_item_id,
    #         message=memory_data.message,
    #         message_from=memory_data.message_from,
    #         session_id=memory_data.session_id,
    #         # context_used=json.dumps(memory_data.context_used) if memory_data.context_used else None
    #     )
        
    #     self.db.add(db_memory)
    #     self.db.commit()
    #     self.db.refresh(db_memory)
    #     return db_memory
    
    # async def get_by_id(self, memory_id: int) -> Optional[ConversationMemory]:
    #     """Get a conversation memory by ID"""
    #     return self.db.query(ConversationMemory).filter(ConversationMemory.id == memory_id).first()
    
    # async def get_by_user_id(
    #     self, 
    #     user_id: str, 
    #     get_most_recent: bool = False,
    #     limit: int = 100,
    #     offset: int = 0
    # ) -> List[ConversationMemory]:
    #     """Get conversation memories by user ID"""
    #     query = self.db.query(ConversationMemory).filter(ConversationMemory.user_id == user_id)
        
    #     if get_most_recent:
    #         # Return only the most recent row
    #         return query.order_by(desc(ConversationMemory.timestamp)).first()
        
    #     # Return paginated results ordered by timestamp (newest first)
    #     return query.order_by(desc(ConversationMemory.timestamp)).offset(offset).limit(limit).all()
    
    # async  def get_by_session_id(
    #     self,
    #     session_id: str,
    #     limit: int = 100,
    #     offset: int = 0,
    #     order_by_recent: bool = True
    # ) -> List[ConversationMemory]:
    #     """
    #     Get all conversation memories by session ID
        
    #     Args:
    #         session_id: The session ID to filter by
    #         limit: Maximum number of results to return
    #         offset: Number of results to skip for pagination
    #         order_by_recent: If True, order by timestamp descending (newest first)
    #                         If False, order by timestamp ascending (oldest first)
        
    #     Returns:
    #         List of ConversationMemory objects
    #     """
    #     query = self.db.query(ConversationMemory).filter(
    #         ConversationMemory.session_id == session_id
    #     )
        
    #     if order_by_recent:
    #         query = query.order_by(desc(ConversationMemory.timestamp))
    #     else:
    #         query = query.order_by(ConversationMemory.timestamp)
        
    #     return query.offset(offset).limit(limit).all()
    
    # async  def get_by_session_id_with_count(
    #     self,
    #     session_id: str,
    #     limit: int = 100,
    #     offset: int = 0,
    #     order_by_recent: bool = True
    # ) -> Tuple[List[ConversationMemory], int]:
    #     """
    #     Get conversation memories by session ID with total count
        
    #     Returns:
    #         Tuple of (memories, total_count)
    #     """
    #     # Get the memories
    #     memories = self.get_by_session_id(session_id, limit, offset, order_by_recent)
        
    #     # Get total count for pagination
    #     total_count = self.db.query(func.count(ConversationMemory.id)).filter(
    #         ConversationMemory.session_id == session_id
    #     ).scalar()
        
    #     return memories, total_count
    
    # async  def get_by_session_and_user(
    #     self,
    #     session_id: str,
    #     user_id: str,
    #     limit: int = 100,
    #     offset: int = 0,
    #     order_by_recent: bool = True
    # ) -> List[ConversationMemory]:
    #     """
    #     Get conversation memories by session ID and user ID
    #     """
    #     query = self.db.query(ConversationMemory).filter(
    #         ConversationMemory.session_id == session_id,
    #         ConversationMemory.user_id == user_id
    #     )
        
    #     if order_by_recent:
    #         query = query.order_by(desc(ConversationMemory.timestamp))
    #     else:
    #         query = query.order_by(ConversationMemory.timestamp)
        
    #     return query.offset(offset).limit(limit).all()
    
    # async  def get_by_user_and_course(
    #     self,
    #     user_id: str,
    #     course_id: str,
    #     get_most_recent: bool = False,
    #     limit: int = 100,
    #     offset: int = 0
    # ) -> Optional[ConversationMemory] | List[ConversationMemory]:
    #     """Get conversation memories by user ID and course ID"""
    #     query = self.db.query(ConversationMemory).filter(
    #         ConversationMemory.user_id == user_id,
    #         ConversationMemory.course_id == course_id
    #     )
        
    #     if get_most_recent:
    #         return query.order_by(desc(ConversationMemory.timestamp)).first()
        
    #     return query.order_by(desc(ConversationMemory.timestamp)).offset(offset).limit(limit).all()
    
    # async  def update(self, memory_id: int, update_data: ConversationMemoryUpdate) -> Optional[ConversationMemory]:
    #     """Update a conversation memory"""
    #     memory = self.get_by_id(memory_id)
    #     if not memory:
    #         return None
        
    #     update_dict = update_data.dict(exclude_unset=True)
        
    #     # Handle context_used conversion if provided
    #     if 'context_used' in update_dict and update_dict['context_used'] is not None:
    #         update_dict['context_used'] = json.dumps(update_dict['context_used'])
        
    #     for field, value in update_dict.items():
    #         setattr(memory, field, value)
        
    #     self.db.commit()
    #     self.db.refresh(memory)
    #     return memory
    
    # async  def delete(self, memory_id: int) -> bool:
    #     """Delete a conversation memory"""
    #     memory = self.get_by_id(memory_id)
    #     if not memory:
    #         return False
        
    #     self.db.delete(memory)
    #     self.db.commit()
    #     return True
    
    # async  def delete_by_session_id(self, session_id: str) -> int:
    #     """Delete all conversation memories for a session ID"""
    #     result = self.db.query(ConversationMemory).filter(
    #         ConversationMemory.session_id == session_id
    #     ).delete()
    #     self.db.commit()
    #     return result
    
    # async  def count_by_user(self, user_id: str) -> int:
    #     """Count total conversation memories for a user"""
    #     return self.db.query(func.count(ConversationMemory.id)).filter(
    #         ConversationMemory.user_id == user_id
    #     ).scalar()
    
    # async  def count_by_session(self, session_id: str) -> int:
    #     """Count total conversation memories for a session"""
    #     return self.db.query(func.count(ConversationMemory.id)).filter(
    #         ConversationMemory.session_id == session_id
    #     ).scalar()
    
    # async  def get_recent_conversations(
    #     self,
    #     user_id: str,
    #     course_id: Optional[str] = None,
    #     hours: int = 24,
    #     limit: int = 50
    # ) -> List[ConversationMemory]:
    #     """Get recent conversations within specified hours"""
    #     from datetime import timedelta
    #     cutoff_time = datetime.now() - timedelta(hours=hours)
        
    #     query = self.db.query(ConversationMemory).filter(
    #         ConversationMemory.user_id == user_id,
    #         ConversationMemory.timestamp >= cutoff_time
    #     )
        
    #     if course_id:
    #         query = query.filter(ConversationMemory.course_id == course_id)
        
    #     return query.order_by(desc(ConversationMemory.timestamp)).limit(limit).all()
    
    # async  def update(self, memory_id: int, update_data: ConversationMemoryUpdate) -> Optional[ConversationMemory]:
    #     """Update a conversation memory"""
    #     memory = self.get_by_id(memory_id)
    #     if not memory:
    #         return None
        
    #     update_dict = update_data.dict(exclude_unset=True)
        
    #     # Handle context_used conversion if provided
    #     if 'context_used' in update_dict and update_dict['context_used'] is not None:
    #         update_dict['context_used'] = json.dumps(update_dict['context_used'])
        
    #     for field, value in update_dict.items():
    #         setattr(memory, field, value)
        
    #     self.db.commit()
    #     self.db.refresh(memory)
    #     return memory
    
    # async  def delete(self, memory_id: int) -> bool:
    #     """Delete a conversation memory"""
    #     memory = self.get_by_id(memory_id)
    #     if not memory:
    #         return False
        
    #     self.db.delete(memory)
    #     self.db.commit()
    #     return True


    # async  def user_exists(self, user_id: str) -> bool:
    #     """Check if a user exists in the database"""
    #     return self.db.query(
    #         exists().where(ConversationMemory.user_id == user_id)
    #     ).scalar()
    
    # async  def generate_random_string(self, length: int = 15) -> str:
    #     """Generate a random string of specified length"""
    #     characters = string.ascii_letters + string.digits
    #     return ''.join(random.choice(characters) for _ in range(length))
    
    # async  def ensure_user_exists_with_welcome_message(
    #     self,
    #     user_context: Dict[str, Any],
    #     welcome_message: str = "Welcome! How can I help you today?",
    #     message_from: str = "assistant"
    # ) -> Tuple[bool, ConversationMemory]:
    #     """
    #     Check if user exists, if not create a welcome message for them.
        
    #     Args:
    #         user_context: Dictionary containing user information
    #         welcome_message: Message to create if user doesn't exist
    #         message_from: Who the message is from ('user' or 'assistant')
        
    #     Returns:
    #         Tuple of (was_created: bool, memory: ConversationMemory)
    #     """
    #     user_id = user_context["user_id"]
        
    #     # Check if user exists
    #     if await self.user_exists(user_id):
    #         # User exists, get their most recent message
    #         recent_memory = await self.get_by_user_id(user_id, get_most_recent=True)
    #         return False, recent_memory
        
    #     # User doesn't exist, create welcome message
    #     # Generate a session ID if not provided in context
    #     session_id = self.generate_random_string(20)
        
    #     # Create the welcome memory
    #     memory_data = ConversationMemoryCreate(
    #         user_id=user_id,
    #         course_id=user_context["course_id"],
    #         # module_item_id=user_context.get("module_item_id"),
    #         message=welcome_message,
    #         message_from=message_from,
    #         session_id=session_id,
    #     )
        
    #     created_memory = await self.create(memory_data)
    #     return True, created_memory

    
    # async  def format_conversations_for_chatbot(
    #     self,
    #     session_id: str,
    #     limit: int = 100,
    # ) -> List[Dict[str, Any]]:
    #     """
    #     Format conversations for chatbot in the required structure.
        
    #     Args:
    #         session_id: Session ID to get conversations for
    #         limit: Maximum number of conversations to return
    #         include_context: Whether to include context information
            
    #     Returns:
    #         List of dictionaries in the format [{'from': 'user', 'message': 'hi'}, ...]
    #     """
    #     # Get conversations for the session
    #     conversations = self.get_by_session_id(session_id, limit=limit, order_by_recent=False)
        
    #     # Format the conversations
    #     formatted_conversations = []
        
    #     for conv in conversations:
    #         # Determine the 'from' field based on message_from
    #         if conv.message_from.lower() in ['user', 'human']:
    #             from_field = 'user'
    #         elif conv.message_from.lower() in ['ai', 'assistant', 'bot', 'system']:
    #             from_field = 'ai'
    #         else:
    #             from_field = conv.message_from.lower()  # fallback
            
    #         conversation_item = {
    #             'from': from_field,
    #             'message': conv.message
    #         }
            
    #         formatted_conversations.append(conversation_item)
        
    #     return formatted_conversations




from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import json

class ConversationMemoryRawRepository_rce:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.table_name = "conversations_rce"

    async def create(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new conversation memory using raw SQL"""
        sql = text("""
            INSERT INTO conversations_rce
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
            SELECT * FROM conversations_rce 
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
                SELECT * FROM conversations_rce 
                WHERE user_id = :user_id 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            params = {'user_id': user_id}
        else:
            sql = text("""
                SELECT * FROM conversations_rce 
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
        limit: int = 1,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all conversation memories by session ID using raw SQL"""
        sql = text("""
            SELECT * FROM conversations_rce 
            WHERE session_id = :session_id 
            ORDER BY timestamp DESC 
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
            FROM conversations_rce 
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
                SELECT 1 FROM conversations_rce 
                WHERE user_id = :user_id
            ) as user_exists
        """)
        
        result = await self.session.execute(sql, {'user_id': user_id})
        return result.scalar()
    
    async def get_most_recent_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent message for a user using raw SQL"""
        sql = text("""
            SELECT * FROM conversations_rce 
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
            INSERT INTO conversations_rce 
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
            INSERT INTO conversations_rce 
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
            UPDATE conversations_rce 
            SET summary = :new_summary
            WHERE id = (
                SELECT id 
                FROM conversations_rce 
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

    
    async def get_latest_summary(self, session_id: str) -> Optional[str]:
        sql = text("""
            SELECT summary 
            FROM conversations_rce 
            WHERE session_id = :session_id 
            AND summary IS NOT NULL
            AND summary != ''
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        params = {
            'session_id': session_id
        }
        
        result = await self.session.execute(sql, params)
        row = result.mappings().first()
        
        if row:
            return row['summary']
        return None

    async def find_similar_conversations(self, session_id: str, embedding: str, limit: int = 5) -> List[Dict[str, Any]]:
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
            FROM conversations_rce 
            WHERE session_id = :session_id
            AND embedding IS NOT NULL
            ORDER BY embedding <=> :embedding
            LIMIT :limit
        """)
        
        params = {
            'session_id': session_id,
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
            UPDATE conversations_rce 
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
    
    async def update_user_evaluation_and_quiz_session_by_session_id(
        self, 
        session_id: str, 
        evaluation: str, 
        quiz_session_id: int,
        quiz_active: bool = False  # Add quiz_active parameter
    ) -> Optional[Dict[str, Any]]:
        """Update evaluation, quiz_session_id, and quiz_active for the most recent conversation of a user"""
        sql = text("""
            UPDATE conversations_rce 
            SET evaluation = :evaluation, 
                quiz_session_id = :quiz_session_id,
                quiz_active = :quiz_active
            WHERE id = (
                SELECT id FROM conversations 
                WHERE session_id = :session_id 
                ORDER BY timestamp DESC 
                LIMIT 1
            )
            RETURNING *
        """)
        
        params = {
            'session_id': session_id,
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
        session_id: str, 
        quiz_active: bool
    ) -> Optional[Dict[str, Any]]:
        """Update only the quiz_active status for the most recent conversation of a user"""
        sql = text("""
            UPDATE conversations_rce
            SET quiz_active = :quiz_active
            WHERE id = (
                SELECT id FROM conversations_rce 
                WHERE session_id = :session_id 
                ORDER BY timestamp DESC 
                LIMIT 1
            )
            RETURNING *
        """)
        
        params = {
            'session_id': session_id,
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
            FROM conversations_rce c
            WHERE c.session_id = :session_id
              AND c.evaluation = 'passed'
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        result = await self.session.execute(sql, {"session_id": session_id})
        row = result.first()
        return row[0] if row else None