from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.table_name = "user_sessions"  # Change to your actual table name
    
    async def get_user_id_by_session_id(self, session_id: str) -> Optional[str]:

        sql = text(f"""
            SELECT user_id FROM {self.table_name} 
            WHERE session_id = :session_id
        """)
        
        result = await self.session.execute(sql, {"session_id": session_id})
        row = result.mappings().first()
        return row["user_id"] if row else None
    
    async def create_session(self, user_id: str, session_id: str) -> Dict[str, Any]:

        sql = text(f"""
            INSERT INTO {self.table_name} (user_id, session_id)
            VALUES (:user_id, :session_id)
            RETURNING *
        """)
        
        result = await self.session.execute(sql, {
            "user_id": user_id,
            "session_id": session_id
        })
        await self.session.commit()
        
        row = result.mappings().first()
        return dict(row) if row else {}
    
    async def session_exists(self, session_id: str) -> bool:

        sql = text(f"""
            SELECT EXISTS(
                SELECT 1 FROM {self.table_name} 
                WHERE session_id = :session_id
            ) as session_exists
        """)
        
        result = await self.session.execute(sql, {"session_id": session_id})
        return result.scalar()


    async def delete_by_session_id(self, session_id: str) -> int:
        """
        Delete all records matching the given session_id.
        Returns the number of rows deleted.
        """
        sql = text(f"""
            DELETE FROM {self.table_name}
            WHERE session_id = :session_id
        """)
        result = await self.session.execute(sql, {"session_id": session_id})
        await self.session.commit()
        return result.rowcount
