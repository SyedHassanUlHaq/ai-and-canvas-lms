import os
import json
import logging
from typing import List, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv
from app.repository.conversation_memory import ConversationMemoryRawRepository
from app.repository.user_sessions import SessionRepository
from app.core.config import embedding_model

# Load environment variables
load_dotenv()

# Conditional imports based on USE_BEDROCK setting
USE_BEDROCK = os.getenv('USE_BEDROCK', 'false').lower() == 'true'

if USE_BEDROCK:
    from .bedrock_service import bedrock_service
    logger = logging.getLogger(__name__)
    logger.info("🤖 Using AWS Bedrock Claude for conversation summarization")
else:
    import google.auth
    from google.cloud import aiplatform
    from vertexai.generative_models import GenerativeModel
    logger = logging.getLogger(__name__)
    logger.info("🤖 Using Google Vertex AI Gemini for conversation summarization")



# from app.repository.vector import CourseChunkRepository 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



@dataclass
class AIResponse:
    """Represents a response from the AI tutor"""
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    suggested_actions: List[str]
    learning_objectives: List[str]

class ConvoSummerizer:
    """AI Tutor using RAG pipeline with either Bedrock Claude or Gemini based on USE_BEDROCK setting"""
    
    def __init__(self, credentials_path: str = "elivision-ai-1-4e63af45bd31.json", project_id: str = 'elivision-ai-1'):
        self.project_id = project_id
        self.credentials_path = credentials_path
        self.use_bedrock = USE_BEDROCK
        
        # Initialize AI service based on USE_BEDROCK setting
        if self.use_bedrock:
            self._initialize_bedrock()
        else:
            self._initialize_gemini()
        
        # Initialize vector store (pgvector by default)
        # self._initialize_vector_store()
        
    def _initialize_bedrock(self):
        """Initialize AWS Bedrock service"""
        try:
            self.bedrock = bedrock_service
            logger.info("✅ AWS Bedrock service initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Bedrock: {e}")
            raise
        
    def _setup_credentials(self):
        """Setup Google Cloud credentials"""
        try:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.credentials_path
            credentials, project = google.auth.default()
            logger.info(f"✅ Successfully authenticated with project: {project}")
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            raise
            
    def _initialize_gemini(self):
        """Initialize Gemini model"""
        try:
            # Setup Google Cloud credentials first
            self._setup_credentials()
            
            # Initialize Gemini
            aiplatform.init(project=self.project_id, location="asia-southeast1")
            self.gemini_model = GenerativeModel("gemini-2.5-flash")
            logger.info("✅ Gemini model initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini: {e}")
            raise
            
    
            
    def _create_tutor_prompt(self, query: str, response: Any, summary: str) -> str:
        """Create a comprehensive prompt for the AI tutor"""
        
        
        # Create the comprehensive prompt
        prompt = f"""You are an ai assisstant whose job is to update the summary of conversation between an AI Tutor, and user. 
        you will take the previous summary along with the user query, and ai response, and then update the summary.

        the user can speak in either english or indonasian. 

        You will always include the module, topic, or course of the conversation in the summary when possible. 

        You will include in every summary the language user speaks as well in a clear fashion. 

        keep in mind that the summary wil be fed to another ai assisstant. make it accordingly

        existing summary: {summary}
        user query: {query}
        ai response: {response}
            """

        return prompt
        
    from app.api.setup_db import AsyncSession
        

    async def summerize(self, user_id, query: str, response: Any, summary: str, session_id: str, evaluation: str, quiz_session_id: int, quiz_active: bool, current_language: str, repo: Any) -> str:
        """Ask a question to the AI tutor"""
        print('500')
        try:
            # Get query embedding
            logger.info(f"🔍 generating summary for: '{query}...'")

            
            # Create the tutor prompt
            prompt = self._create_tutor_prompt(query, response, summary)
            
            logger.info("🤖 Generating Summary")
            logger.info(f"🤖 Using {'Bedrock' if self.use_bedrock else 'Gemini'} for summarization")
            
            # Generate summary using the appropriate AI service
            if self.use_bedrock:
                summary = self.bedrock.generate_content(prompt)
            else:
                summary_response = self.gemini_model.generate_content(prompt)
                summary = summary_response.text



            
            # Log response summary
            logger.info(f"  summary generated successfully: {summary}")

            embeddings = embedding_model.get_embeddings([response])
            query_embedding = embeddings[0].values

            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"



            params = {
                'user_id': user_id,
                'course_id': None,
                'module_item_id': None,
                'message': response,
                'message_from': 'ai',
                'session_id': session_id,
                'summary': summary,
                'embedding': embedding_str,
                'evaluation': evaluation,
                'quiz_session_id': quiz_session_id,
                'quiz_active': quiz_active,
                'current_language': current_language
            }

            rec = await repo.create(params)

            logger.info('response added in conversation: ', rec)

            return summary
            # logger.info(f"   Top similarity: {max([chunk['similarity'] for chunk in relevant_chunks]) if relevant_chunks else 0:.4f}")
            
            
        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            return None

    async def update_summary_in_db(self, session_id: str, summary: str, db: AsyncSession = None) -> bool:
        logger.info('  Updating summary for session id: ', session_id)
        outer_repo = SessionRepository(db)
        user_id = outer_repo.get_user_id_by_session_id(session_id)

        convo_repo = ConversationMemoryRawRepository(db)
        
    
    async def summerize_rce(self, query: str, response: Any, summary: str, session_id: str, repo: Any) -> str:
        """Ask a question to the AI tutor"""
        print('500')
        try:
            # Get query embedding
            logger.info(f"🔍 generating summary for: '{query}...'")

            
            # Create the tutor prompt
            prompt = self._create_tutor_prompt(query, response, summary)
            
            logger.info("🤖 Generating Summary")
            logger.info(f"🤖 Using {'Bedrock' if self.use_bedrock else 'Gemini'} for summarization")
            
            # Generate summary using the appropriate AI service
            if self.use_bedrock:
                summary = self.bedrock.generate_content(prompt)
            else:
                summary_response = self.gemini_model.generate_content(prompt)
                summary = summary_response.text

            # Log response summary
            logger.info(f"  summary generated successfully: {summary}")

            embeddings = embedding_model.get_embeddings([response])
            query_embedding = embeddings[0].values

            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            params = {
                'user_id': None,
                'course_id': None,
                'module_item_id': None,
                'message': response,
                'message_from': 'ai',
                'session_id': session_id,
                'summary': summary,
                'embedding': embedding_str
            }

            rec = await repo.create(params)

            logger.info('response added in conversation: ', rec)

            return summary            
            
        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            return None




summary_creator = ConvoSummerizer()