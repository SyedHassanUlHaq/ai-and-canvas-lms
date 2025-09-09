from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, List, Optional, Any

class QuizQuestionsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.table_name = "quiz_questions"  # Table name as property
    
    async def create_question(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new quiz question"""
        sql = text(f"""
            INSERT INTO {self.table_name} 
            (question_number, difficulty, question_type, question_text, options, expected_answer, explanation, quiz_session_id)
            VALUES (:question_number, :difficulty, :question_type, :question_text, :options, :expected_answer, :explanation, :quiz_session_id)
            RETURNING *
        """)
        
        params = {
            'question_number': question_data['question_number'],
            'difficulty': question_data['difficulty'],
            'question_type': question_data['question_type'],
            'question_text': question_data['question_text'],
            'options': question_data.get('options'),
            'expected_answer': question_data['expected_answer'],
            'explanation': question_data.get('explanation'),
            'quiz_session_id': question_data.get('quiz_session_id')
        }
        
        result = await self.session.execute(sql, params)
        await self.session.commit()
        return dict(result.mappings().first())
    
    async def get_question_by_id(self, question_id: int) -> Optional[Dict[str, Any]]:
        """Get quiz question by ID"""
        sql = text(f"""
            SELECT * FROM {self.table_name} 
            WHERE id = :question_id
        """)
        
        result = await self.session.execute(sql, {"question_id": question_id})
        row = result.mappings().first()
        return dict(row) if row else None
    
    async def get_questions_by_session_id(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all questions for a quiz session"""
        sql = text(f"""
            SELECT * FROM {self.table_name} 
            WHERE quiz_session_id = :session_id 
            ORDER BY question_number ASC
        """)
        
        result = await self.session.execute(sql, {"session_id": session_id})
        return [dict(row) for row in result.mappings().all()]
    
    async def get_questions_by_difficulty(
        self, 
        difficulty: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get questions by difficulty level"""
        sql = text(f"""
            SELECT * FROM {self.table_name} 
            WHERE difficulty = :difficulty 
            ORDER BY question_number ASC 
            LIMIT :limit
        """)
        
        result = await self.session.execute(sql, {
            'difficulty': difficulty,
            'limit': limit
        })
        
        return [dict(row) for row in result.mappings().all()]