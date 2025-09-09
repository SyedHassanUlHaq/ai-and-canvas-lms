from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, List, Optional, Any


class QuizSessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.table_name = "quiz_session"  # Table name as property
    
    async def create_quiz_session(self) -> Dict[str, Any]:
        """Create a new quiz session (no parameters required)"""
        sql = text(f"""
            INSERT INTO {self.table_name} (created_at, updated_at)
            VALUES (CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING *
        """)
        
        result = await self.session.execute(sql)
        await self.session.commit()
        return dict(result.mappings().first())