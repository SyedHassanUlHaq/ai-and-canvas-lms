from app.repository.conversation_memory import *
import logging


logger = logging.getLogger(__name__)

async def get_quiz_questions_for_user(user_record, quiz_questions_repo):
    quiz_id = user_record['quiz_question_id']
    evaluation = user_record['evaluation']
    if not quiz_id:
        #No quiz found for session
        logger.info(f"No quiz id found for user: {user_record}")
        return None
    if not evaluation:
        #No quiz found for session
        logger.info(f"No evaluation found for user: {user_record}")
        return None
    
    return quiz_questions_repo.get_questions_by_session_id(user_record['session_id'])
    
    
         



async def get_difficulty_by_quiz_session_id(quiz_id: int, quiz_repo) -> Optional[str]:
    """Get the difficulty level for a specific quiz session"""
    # Get all questions for the quiz session
    questions = await quiz_repo.get_questions_by_session_id(quiz_id)
    print(questions)
    
    if not questions:
        return 'easy'

    if questions[0].get('difficulty') == 'easy':
        return 'medium'
    else:
        return 'hard'
    
    # Return the difficulty from the first question (assuming all questions in a session have same difficulty)
    # return questions[0].get('difficulty')


