
import os
import json
import logging
from typing import List, Dict, Any
from dataclasses import dataclass
from app.api.setup_db import get_top_5_content
import google.auth
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel

import hashlib
# from app.repository.vector import CourseChunkRepository 
from app.core.config import Settings



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiEmbeddingModel:
    """Improved hash-based embedding model for semantic-like behavior"""
    
    def __init__(self, project_id: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        self.use_real_embeddings = False
        self.embedding_method = "improved_hash"
        logger.info("✅ Using improved hash-based embeddings for semantic-like behavior")

    
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of texts using improved hash-based method"""
        return self._get_improved_hash_embeddings(texts)

    def get_similar_chunks(query_embedding: List[float], top_k: int = 3, connection_string: str = Settings.connection_url) -> List[Dict[str, Any]]:

        # Initialize repository (you might want to make this a singleton in production)
        # if connection_string is None:
        #     # Default connection string - replace with your actual connection details
        #     connection_string = "postgresql://user:password@localhost:5432/your_database" #TODO

        repository = CourseChunkRepository(connection_string)

        try:
            # Search for similar chunks
            similar_chunks = repository.search_similar_chunks(query_embedding, top_k=top_k)

            logger.info(f"✅ Found {len(similar_chunks)} similar chunks")

            # Format and return the results
            formatted_results = []
            for chunk in similar_chunks:
                formatted_chunk = {
                    # 'id': chunk['id'],
                    'content': chunk['content'],
                    'similarity_score': chunk['similarity'],
                    # 'chunk_type': chunk['chunk_type'],
                    # 'metadata': chunk['metadata'],
                    # 'parent_id': chunk['parent_id'],
                    # 'related_ids': chunk['related_ids']
                }
                formatted_results.append(formatted_chunk)

            return formatted_results

        except Exception as e:
            logger.error(f"❌ Error retrieving similar chunks: {e}")
            return []
    
    def _get_improved_hash_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Improved hash-based embedding method with better semantic-like behavior"""
        embeddings = []
        
        for text in texts:
            # Preprocess text for better semantic grouping
            processed_text = self._preprocess_text(text)
            
            # Create multiple hash-based features for better semantic behavior
            embedding = []
            
            # 1. Main content hash (64 dimensions)
            hash_obj = hashlib.sha256(processed_text.encode())
            content_hash = [float(int(hash_obj.hexdigest()[i:i+2], 16)) / 255.0 
                          for i in range(0, 64, 2)]
            embedding.extend(content_hash)
            
            # 2. Word-based features (32 dimensions)
            words = processed_text.lower().split()
            word_features = self._get_word_features(words)
            embedding.extend(word_features)
            
            # 3. Length and structure features (32 dimensions)
            structure_features = self._get_structure_features(processed_text)
            embedding.extend(structure_features)
            
            # 4. Topic indicators (16 dimensions)
            topic_features = self._get_topic_features(processed_text)
            embedding.extend(topic_features)
            
            # Total: 144 dimensions (much better than 64)
            embeddings.append(embedding)
        
        return embeddings
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better semantic grouping"""
        import re
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep important ones
        text = re.sub(r'[^\w\s\-\.]', '', text)
        
        return text.strip()
    
    def _get_word_features(self, words: List[str]) -> List[float]:
        """Extract word-based features for semantic grouping"""
        features = []
        
        # Common psychology/leadership/design thinking terms
        psychology_terms = ['psychology', 'behavior', 'mind', 'brain', 'emotion', 'learning', 'memory']
        leadership_terms = ['leadership', 'grit', 'growth', 'mindset', 'resilience', 'motivation']
        design_terms = ['design', 'thinking', 'empathy', 'user', 'prototype', 'ideation']
        
        # Calculate term frequency scores
        psych_score = sum(1 for word in words if word in psychology_terms) / max(len(words), 1)
        leader_score = sum(1 for word in words if word in leadership_terms) / max(len(words), 1)
        design_score = sum(1 for word in words if word in design_terms) / max(len(words), 1)
        
        # Add scores and additional features
        features.extend([psych_score, leader_score, design_score])
        
        # Add word count features
        features.append(min(len(words) / 100.0, 1.0))  # Normalized word count
        
        # Add remaining dimensions with hash-based values
        remaining_dims = 32 - len(features)
        hash_obj = hashlib.md5(str(words).encode())
        for i in range(remaining_dims):
            features.append(float(int(hash_obj.hexdigest()[i:i+2], 16)) / 255.0)
        
        return features[:32]  # Ensure exactly 32 dimensions
    
    def _get_structure_features(self, text: str) -> List[float]:
        """Extract structural features from text"""
        features = []
        
        # Text length features
        features.append(min(len(text) / 1000.0, 1.0))  # Normalized length
        
        # Sentence count (rough estimate)
        sentences = text.split('.')
        features.append(min(len(sentences) / 20.0, 1.0))
        
        # Paragraph indicators
        paragraphs = text.split('\n\n')
        features.append(min(len(paragraphs) / 10.0, 1.0))
        
        # Add remaining dimensions
        remaining_dims = 32 - len(features)
        hash_obj = hashlib.md5(text.encode())
        for i in range(remaining_dims):
            features.append(float(int(hash_obj.hexdigest()[i:i+2], 16)) / 255.0)
        
        return features[:32]
    
    def _get_topic_features(self, text: str) -> List[float]:
        """Extract topic-related features"""
        features = []
        
        # Topic indicators based on content
        if any(word in text for word in ['psychology', 'behavior', 'brain']):
            features.append(1.0)  # Psychology topic
        else:
            features.append(0.0)
            
        if any(word in text for word in ['leadership', 'grit', 'growth']):
            features.append(1.0)  # Leadership topic
        else:
            features.append(0.0)
            
        if any(word in text for word in ['design', 'empathy', 'prototype']):
            features.append(1.0)  # Design thinking topic
        else:
            features.append(0.0)
        
        # Add remaining dimensions
        remaining_dims = 16 - len(features)
        hash_obj = hashlib.md5(text.encode())
        for i in range(remaining_dims):
            features.append(float(int(hash_obj.hexdigest()[i:i+2], 16)) / 255.0)
        
        return features[:16]



"""
AI Tutor Configuration
=====================

Configuration settings for the AI Tutor RAG pipeline
"""

import os
from typing import Dict, Any

class TutorConfig:
    """Configuration class for AI Tutor"""
    
    # Google Cloud Configuration
    PROJECT_ID = "elivision-ai-1"
    LOCATION = "us-central1"
    CREDENTIALS_PATH = "elivision-ai-1-4e63af45bd31.json"
    
    # Model Configuration
    MODEL_NAME = "gemini-1.5-pro"
    MAX_TOKENS = 2048
    TEMPERATURE = 0.7
    
    # Vector Store Configuration
    TOP_K_RESULTS = 3
    SIMILARITY_THRESHOLD = 0.7
    
    # Course Configuration
    COURSE_NAME = "[DEMO] Introduction to Design Thinking Demo"
    COURSE_ID = "240"
    
    # Tutor Personality
    TUTOR_PERSONALITY = {
        "tone": "encouraging and supportive",
        "style": "clear and engaging",
        "approach": "student-centered",
        "expertise": "design thinking, psychology, leadership"
    }
    
    # Learning Objectives
    LEARNING_OBJECTIVES = [
        "Understand and articulate core design thinking principles",
        "Apply psychological concepts to real-world situations", 
        "Develop leadership skills through GRIT and growth mindset",
        "Build emotional intelligence and empathy",
        "Master scientific methods and critical thinking"
    ]
    
    # Response Templates
    RESPONSE_TEMPLATES = {
        "greeting": "Hello! I'm your AI tutor for {course_name}. How can I help you learn today?",
        "encouragement": "Great question! Let me help you understand this concept better.",
        "clarification": "I want to make sure I understand your question correctly. Could you clarify...",
        "suggestion": "Here's a helpful approach to think about this...",
        "next_steps": "To deepen your understanding, I suggest..."
    }
    
    @classmethod
    def get_model_config(cls) -> Dict[str, Any]:
        """Get model configuration"""
        return {
            "model_name": cls.MODEL_NAME,
            "max_tokens": cls.MAX_TOKENS,
            "temperature": cls.TEMPERATURE,
            "top_k": cls.TOP_K_RESULTS,
            "similarity_threshold": cls.SIMILARITY_THRESHOLD
        }
    
    @classmethod
    def get_tutor_prompt_template(cls) -> str:
        """Get the base tutor prompt template"""
        return f"""You are an expert AI tutor for the course: {cls.COURSE_NAME}

            Your role is to help students learn effectively by providing clear, engaging, and personalized explanations.

            COURSE OVERVIEW:
            This course covers multiple interconnected topics:
            - Design Thinking: User-centered innovation and problem-solving
            - Psychology: Scientific study of mind and behavior  
            - Leadership Development: GRIT, growth mindset, and emotional intelligence
            - Brain Science: Understanding neural processes and behavior

            TUTOR PERSONALITY:
            - Be {cls.TUTOR_PERSONALITY['tone']} and {cls.TUTOR_PERSONALITY['style']}
            - Use a {cls.TUTOR_PERSONALITY['approach']} approach
            - Draw from your expertise in {cls.TUTOR_PERSONALITY['expertise']}

            LEARNING OBJECTIVES:
            {chr(10).join(f"- {obj}" for obj in cls.LEARNING_OBJECTIVES)}

            When responding to students:
            1. Use the provided course material as your primary knowledge source
            2. Provide clear, step-by-step explanations
            3. Connect concepts to real-world applications
            4. Encourage critical thinking and reflection
            5. Suggest related topics and next steps
            6. Be patient and supportive of different learning styles

            Remember: Your goal is to help students not just memorize information, but truly understand and apply these concepts in their personal and professional lives.""" 


@dataclass
class TutorResponse:
    """Represents a response from the AI tutor"""
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    suggested_actions: List[str]
    learning_objectives: List[str]

class AITutor:
    """AI Tutor using RAG pipeline with Gemini"""
    
    def __init__(self, credentials_path: str = "elivision-ai-1-4e63af45bd31.json", project_id: str = 'elivision-ai-1'):
        self.project_id = project_id
        self.credentials_path = credentials_path
        
        # Initialize Google Cloud credentials FIRST
        self._setup_credentials()
        
        # Then initialize models
        self._initialize_gemini()
        # self._initialize_embedding_model()
        
        
        self.conversation_history = []
        self.student_profile = {}
        
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
            aiplatform.init(project=self.project_id, location="us-central1")
            self.gemini_model = GenerativeModel("gemini-2.5-pro")
            logger.info("✅ Gemini model initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini: {e}")
            raise
            

            
    def _create_tutor_prompt(self, query: str, relevant_chunks: List[Dict], summary: str, similar_convo: Any, history: Any = None) -> str:
        """Create a comprehensive prompt for the AI tutor"""

        if len(history) > 6:
            history = history[-5:]

        
        # Create the comprehensive prompt
        prompt = f"""You are an expert AI tutor for a course on Design Thinking, Psychology, and Leadership Development. 
            Your role is to help students learn effectively by providing clear, engaging, and personalized explanations. 

            ### CONTEXT
            Summary of the conversation so far: {summary}
            Relevant information from earlier: {similar_convo}
            Most recent messages: {history}


           ### RELEVANT COURSE MATERIAL:
            {relevant_chunks}

            ### INSTRUCTIONS:
            1. Always respond in Indonesian unless the student's primary language for their current message is English. If a user asks a question entirely in English, respond in English for that turn.
            2. Answer the student's question using the provided course material
            3. If the user asks a question about somehting, explain the most relevant information from the provided relavant course material to answer the student's question. 
            3. ALWAYS USE CONTEXT to give your response.
            4. even if the course material does not explicitly include the topic student is interested in, still generate an approriate response based on the results.
            5. Keep your answers very short
            6. Your primary goal is to act as a supportive and encouraging tutor. Provide clear, step-by-step explanations for any concepts the student is struggling with. 
            7. Do not tell the user if you can't find anything. remember that you're part of the organization. 
            8. Do not tell the user of any errors. 
            9. Be encouraging and supportive in your tone
            11. Connect concepts to real-world applications
            12. Suggest related topics or next steps for learning
            13. If the question goes beyond the course material, acknowledge this and suggest where they might find more information
            14. If the student asks you to quiz them, generate a quiz for them using the course material and any specific topics the user asks to quiz them on. the difficulty of the quiz should be based on the current context, and past conversation history. 
            15. When the user asks for a quiz, generate a 10-question quiz. Ask one question at a time. After the user answers a question, provide immediate feedback on whether their answer was correct or incorrect before asking the next question. 
            16. After the user answers all of the qeustions, tell them how many they got right, and how many they got wrong. Say an appropriate message based on the results. 
            17. If the user got atleast 8 questions right, then increase the difficulty fot the next time. 
            18. After the quiz is done, ask the user if they'd like another quiz. 

            
            
            
            ### Quiz examples
            Example 1: Multiple Choice Question
                This is a straightforward format that is good for checking basic recall and understanding.

                Alright, let's start! Here's your first question:

                Which of the following is NOT one of the five stages of Design Thinking?

                A) Empathize
                B) Define
                C) Ideate
                D) Analyze
                E) Prototype
                F) Test

                Take your time and let me know your answer. 

            Example 2: Short Answer/Concept Application Question
                This type of question requires the student to think more deeply and apply a concept, which is great for assessing comprehension.

                Great, here's the next one!

                We've been talking a lot about GRIT. Can you explain in your own words how a growth mindset is connected to having grit?

                There's no wrong answer here, just share what you think!
                
            Example 3: True or False Question
                Simple and quick, this format is useful for a fast knowledge check on a specific fact or principle.

                Question number 3!

                True or False: The limbic system of the brain is primarily responsible for logical reasoning and problem-solving.

                What do you think?
                
            Example 4: Scenario-Based Question
                This is a more advanced question that asks the student to apply what they've learned to a realistic situation. It's excellent for testing problem-solving skills.

                You're doing great! Here's a challenge for you.

                Imagine you're a team leader working on a new project. A team member is struggling with a difficult task and seems very frustrated. Using your understanding of social and emotional intelligence, what is one way you could respond to this team member to show empathy and support?
                
            Example 5: Mixed Difficulty Example
                This example shows how to combine different question types to create a more dynamic and engaging quiz.

                Excellent work so far! Let's try this one.

                Question 4:
                We've learned about the scientific method in psychology. Imagine you want to test if listening to music helps students focus better while studying. What would be your **hypothesis** for this experiment?

                Take a moment and think it through. You got this!



            ###Post Quiz Examples
            
            A good post-quiz conversation should be brief, informative, and encouraging. It's important to provide a clear summary of the results and suggest a next step. Here are some examples you can use to guide your AI tutor bot.
            
            - Example 1: The Student Did Well
            - This response is positive and encourages the student to continue to the next level of difficulty.
            
            - Luar biasa! You answered 9 out of 10 questions correctly. That's a fantastic result! It shows you have a strong grasp of the material.
            
            - Since you did so well, I've noted that we can increase the difficulty for our next quiz. Would you like to try another quiz on a different topic?
            
            - Example 2: The Student Had Mixed Results
            - This response is supportive and focuses on the positive while acknowledging areas for improvement.
            
            - Great effort! You got 7 out of 10 questions right. That's a good score, and it's clear you're understanding the key concepts.
            
            - Let's review the questions you missed. Would you like to go over those topics now, or would you prefer to try another quiz?
            
            - Example 3: The Student Struggled
            - This response is empathetic and offers a path forward without being discouraging. It focuses on growth rather than the score itself.
            
            - No worries at all! You got 4 out of 10 questions correct this time. Remember, the goal is to learn, not just to get a perfect score. We've got this!
            
            - Let's take a look at the questions you found tricky. I can provide some more explanation





            ### STUDENT QUERY: {query}

            Please provide a conise and helpful response that demonstrates your expertise as an AI tutor. make it easy to read by making bullet points when possible
            """

        return prompt
        
    
    from app.api.setup_db import get_top_5_content, AsyncSession
        

    async def ask_question(self, question: str, summary: str = None, similar_past_convo: Any = None, history: Any = None, db: AsyncSession = None) -> TutorResponse:
        """Ask a question to the AI tutor"""
        
        try:
            # Get query embedding
            logger.info(f"🔍 Processing question: '{question}...'")

            
            # query_embedding = self.embedding_model.get_embeddings([question])[0]
            
            # Search for relevant chunks
            logger.info(f"📚 Searching knowledge base for relevant content...")
            response = await get_top_5_content(question, db)
            print('RESPONSE', response)
            relevant_chunks = response
            # relevant_chunks = self.vector_store.search(query_embedding, top_k=3)
            
            # Log detailed retrieval results
            logger.info(f"✅ Retrieved {len(relevant_chunks)} chunks from knowledge base:")
            # total_chunks_in_kb = len(self.vector_store.chunks)
            # logger.info(f"📊 Total chunks in knowledge base: {total_chunks_in_kb}")

            contents = ''
            
            for i, chunk_data in enumerate(relevant_chunks):
                print(i, chunk_data)
                content = chunk_data['content']
                contents = contents + content + " ...\n\n "
            
            # Create conversation history for this student
            
            
            # Create the tutor prompt
            prompt = self._create_tutor_prompt(question, summary, similar_past_convo, contents, history)
            print("-"*50)
            # Generate response using Gemini
            logger.info("🤖 Generating AI tutor response...")
            response = self.gemini_model.generate_content(prompt)
            answer = response.text


            
            # Create response object
            tutor_response = TutorResponse(
                answer=answer,
                confidence=0.5,
                sources=[{
                    'content': chunk['content'] + "...",
                    'metadata': chunk['doc_name'] + "\n " + chunk['module_name'],
                    'similarity': 0.5
                } for chunk in relevant_chunks],
                suggested_actions=['nothing'],
                learning_objectives=['develop']
            )
            
            # Log response summary
            logger.info(f"🎯 Response generated successfully!")
            logger.info(f"   Confidence: {0.5}")
            logger.info(f"   Sources used: {len(relevant_chunks)}")
            

            return tutor_response
            
        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            return TutorResponse(
                answer="I apologize, but I encountered an error while processing your question. Please try again.",
                confidence=0.0,
                sources=[],
                suggested_actions=["Try rephrasing your question", "Check your internet connection"],
                learning_objectives=[]
            )
            
    