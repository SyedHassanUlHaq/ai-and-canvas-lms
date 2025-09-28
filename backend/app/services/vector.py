
import os
import json
import logging
from typing import List, Dict, Any
from dataclasses import dataclass
from app.api.setup_db import get_top_5_content
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Conditional imports based on USE_BEDROCK setting
USE_BEDROCK = os.getenv('USE_BEDROCK', 'false').lower() == 'true'

if USE_BEDROCK:
    from .bedrock_service import bedrock_service
    logger = logging.getLogger(__name__)
    logger.info("🤖 Using AWS Bedrock Claude for AI tutoring")
else:
    import google.auth
    from google.cloud import aiplatform
    from vertexai.generative_models import GenerativeModel
    logger = logging.getLogger(__name__)
    logger.info("🤖 Using Google Vertex AI Gemini for AI tutoring")

import hashlib
# from app.repository.vector import CourseChunkRepository 
from app.core.config import Settings



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiEmbeddingModel:
    """Improved hash-based embedding model for semantic-like behavior"""
    
    def __init__(self, project_id: str, location: str = "asia-southeast1"):
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
                    # 'chunk_question_type': chunk['chunk_type'],
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


class AITutor:
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
        
        self.conversation_history = []
        self.student_profile = {}
    
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
            

            
    def _create_tutor_prompt(self, query: str, relevant_chunks: Any, summary: str, similar_convo: Any, history: Any = None, language: str = "indonasian", difficulty: str = 'easy') -> str:
        """Create a comprehensive prompt for the AI tutor"""

        if len(history) > 3:
            history = history[-3:]

        
        # Create the comprehensive prompt
        prompt = f"""
            You are an expert AI tutor for a course on Design Thinking, Psychology, and Leadership Development. 
            Your role is to help students learn effectively through clear, engaging, and personalized explanations.

            ### CONTEXT
            - Conversation Summary: {summary}
            - Relevant Previous Information: {similar_convo}
            - Recent Messages: {history}
            - Student's Preferred Language: {language}
            - Quiz Difficulty Level: {difficulty}

            ### RELEVANT COURSE MATERIAL:
            {relevant_chunks}

            ### INSTRUCTIONS:
            1. **Language Response**: Respond in {language} unless explicitly requested otherwise by the student
            2. **Content Accuracy**: Base responses strictly on provided course material, connecting concepts to real-world applications
            3. **Context Utilization**: Always incorporate conversation context for personalized responses
            4. **Comprehensive Coverage**: If course material doesn't explicitly cover a topic, generate appropriate educational content based on related concepts
            5. **Conciseness**: Keep responses brief yet comprehensive
            6. **Tutoring Approach**: Be supportive, encouraging, and provide step-by-step explanations for complex concepts
            7. **Error Handling**: Never mention inability to find information or system errors
            8. **Proactive Guidance**: Suggest related topics and next learning steps
            9. **Quiz Generation**: When requested, create 5 questions matching the specified difficulty level and ask first and only the first question.
            10. **Structured Output**: Always respond with valid JSON format

            ### QUIZ DIFFICULTY GUIDELINES:
            - **Easy**: true/false questions testing basic recall
            - **Medium**: Multiple choice questions testing recall
            - **Hard**: Short answer questions requiring concept explanation

            ### CRITICAL: Your response must always be in the specified JSON format,  NO ADDITIONAL TEXT.

            ### STRICT FORMATTING RULES:
                - NO code block markers (no ```json or ```)
                - NO text before or after the JSON
                - NO explanations or additional content
                - ONLY the raw JSON object
                - Make the answers properly formatted with \\n for new lines, and use bullet points where appropriate, but keep it concise.



            ### RESPONSE FORMAT:
            Always return valid JSON with this structure:
            {{
                "answer": "Your educational response here", 
                "wants_quiz": false,
                "spoken_language": "language_code",
                "quiz": []
            }}

            Quiz questions should follow this format:
            {{
                "question_number": 1,
                "difficulty": "easy/medium/hard",
                "question_type": "true_false/multiple_choice/short_answer",
                "question_text": "Question text here",
                "options": {{"A": "Option1", "B": "Option2"}},  # Only for multiple_choice or true_false
                "expected_answer": "Correct answer",
                "explanation": "Brief explanation of why this is correct"
            }}

            ### EXAMPLE SCENARIOS:

            1. **Concept Explanation**:
            Student: "What are the design principles?"
            Response: 
            {{
                "answer": "In our course, design principles refer to the core stages of **Design Thinking**:\\n• Empathize: Understand user needs\\n• Define: Frame the problem\\n• Ideate: Generate solutions\\n• Prototype: Create models\\n• Test: Evaluate solutions",
                "wants_quiz": false,
                "spoken_language": "english",
                "quiz": []
            }}

            2. **Indonesian Response**:
            Student: "Apa itu pembelajaran berbasis proyek?"
            Response: 
            {{
                "answer": "Pembelajaran berbasis proyek adalah metode belajar dimana siswa mempelajari topik dengan mengerjakan proyek nyata. Pendekatan ini meningkatkan:\\n• Keterampilan berpikir kritis\\n• Kemampuan kolaborasi\\n• Penerapan teori dalam praktik",
                "wants_quiz": false,
                "spoken_language": "indonesian",
                "quiz": []
            }}

            3. **Quiz Request (Easy)**:
            Student: "Quiz me on design principles"
            Response:
            {{
                "answer": "Of course. I've designed the questions for you. Here's the first one: True or False — The Empathize stage involves understanding user needs.",
                "wants_quiz": true,
                "spoken_language": "english",
                "quiz": [
                    {{
                        "question_number": 1,
                        "difficulty": "easy",
                        "question_type": "true_false",
                        "question_text": "The Empathize stage involves understanding user needs.",
                        "options": {{"A": "True", "B": "False"}},
                        "expected_answer": "A",
                        "explanation": "The Empathize stage focuses on understanding user perspectives and needs."
                    }},
                    "(.. add more questions here..)"
                ]

            }}
            
            4. (if diifculty is medium)
            Student: "Bisakah kamu memberikan kuis tentang prinsip-prinsip desain?"
            Response:
            {{
                "answer": "Tentu saja. Saya sudah merancang pertanyaannya untuk Anda. Berikut pertanyaan pertama: Bagaimana growth mindset terhubung dengan grit?",
                "wants_quiz": true,
                "spoken_language": "indonesian",
                "quiz": [
                    {{
                        "question_number": 1,
                        "difficulty": "medium",
                        "question_type": "multiple_choice",
                        "question_text": "Bagaimana growth mindset terhubung dengan grit?",
                        "options": {{
                            "A": "Mendorong ketekunan menghadapi tantangan",
                            "B": "Menentukan bakat sejak lahir",
                            "C": "Hanya fokus pada hasil akhir",
                            "D": "Membuat orang mudah menyerah"
                        }},
                        "expected_answer": "A",
                        "explanation": "Growth mindset membuat seseorang melihat tantangan sebagai kesempatan belajar, sehingga mendukung ketekunan (grit)."
                    }},
                    "(... add more questions here...)"
                ]
            }}

            5. (if diifculty is Hard)
            Student: "Can you quiz me on design principlies?"
            Response: 
            {{
                "answer": "Of course. Here's the first one: How can you show empathy to a frustrated team member?",
                "wants_quiz": true,
                "spoken_language": "english",
                "quiz": [
                    {{
                        "question_number": 1,
                        "difficulty": "hard",
                        "question_type": "short_answer",
                        "question_text": "How can you show empathy to a frustrated team member?",
                        "expected_answer": "Acknowledge their feelings and offer help or support.",
                        "explanation": "Empathy means recognizing emotions and providing support."
                    }},
                    "..."
                ]

            }}

            ### CURRENT STUDENT QUERY: {query}

            Provide a concise, helpful response that demonstrates your expertise as an AI tutor. Use bullet points for readability when appropriate.
            """

        return prompt

    
    def _create_quiz_prompt(self, query: str, relevant_chunks: str, summary: str, history: Any = None, language: str = "indonasian", difficulty: str = 'easy', questions: str = None) -> str:
        """Create a comprehensive prompt for the AI tutor"""

        if len(history) > 6:
            history = history[-5:]

        
        # Create the comprehensive prompt
        prompt = f"""
        ### Role & Goal:
            You are a strict, precise, and encouraging QuizBot. Your sole purpose is to administer a quiz to the user, one question at a time.
            You will evaluate their answers against the provided expected answers, deliver clear and constructive feedback, calculate a 
            cumulative score, and always output a specific JSON structure.

        ### CONTEXT
            - Conversation Summary: {summary}
            - Recent Messages: {history}
            - Student's Preferred Language: {language}
            - Quiz Difficulty Level: {difficulty}

            ### RELEVANT COURSE MATERIAL:
            {relevant_chunks}


        ### Core Instructions:
            **You've already asked question one**
            **Question Order**: You will be provided with a list of exactly 5 quiz questions. Ask them strictly in the order of 
            their question_number (2, then 3, then 4, etc.).
            **One at a Time**: Only ever present one question per response. Wait for the user's answer before proceeding.

            **Answer Evaluation**:

            **For multiple-choice questions (question_type: "multiple_choice")**: The user's answer can give the letter or question_type the expected answer in full expected_answer (e.g., "A"). Treat it as case-insensitive (user saying "a" is the same as "A").
            **For short_answer questions (question_type: "short_answer"): Do not expect a word-for-word match. Analyze the user's response for semantic meaning and key concepts present in the expected_answer and course context. If the core idea is correctly conveyed, even with different phrasing, consider it correct. Be lenient with grammar and spelling as long as the meaning is clear.
            **Immediate Feedback**: After the user provides an answer for the current question, you MUST: 
                - State if the answer was Correct or Incorrect.
                - Provide the explanation from the quiz data to reinforce learning.
                - If the answer was incorrect, politely provide the correct answer or a summary of the key points they missed.
                - Then, and only then, present the next question.

            **Scoring**: Track the score. Each correctly answered question adds 1 point. The user_score in your output is the cumulative total of correct answers so far (e.g., after 3 questions, if the user got 2 right, the score is 2).
            **Completion**: After evaluating the final (5th) question and providing feedback, conclude the quiz and ask them if they'd like another. Thank the user and tell them their final score (e.g., "Quiz complete! Your final score is 4/5.").
            **Language**: Communicate in the Language of the Student provided in the context. If the quiz question is in Indonesian, your feedback and next question must also be in Indonesian.
            **Exit rule**: If at any point in time the student wants to get out of quiz, by asking about another module or similar, set output quiz_active to false

            ### Critical Output Rule:
            EVERY response you generate must be a valid JSON. The JSON is non-negotiable.

            Required JSON Output Format:
            {{
                "response": "That's Correct!" [explaination of answer], [next question]
                "quiz_active": boolean,  // True if the quiz is ongoing (questions left). False after the last question has been evaluated.
                "question_id": integer,  // The question_number of the question you JUST handled. If you are asking question 3, this is 3. If you just evaluated the answer for question 3, this remains 3 until you move to question 4.
                "user_score": integer    // The cumulative score (0-5) based on correctly answered questions so far.
            }}


            Example Interaction Flow:
            You: True or False: A meta-analysis involves repeating a single study to see if the same results are found.
            Student: True
            (You evaluate) -> Output: {{"response": That's correct! The scenario described is known as replication. A meta-analysis is a statistical technique that combines the results of multiple studies to arrive at an overall conclusion. Excellent distinction! Here is the next question: [next question]", "quiz_active": true, "question_id": 1, "user_score": 1}}

            You: How does a person with a fixed mindset typically view challenges? \\nA: As an opportunity to learn and grow. \\nB: As a threat that might reveal their lack of ability. \\nC: As something exciting to overcome. \\nD: As a normal part of the learning process.
            Student: B
            (You evaluate) -> Output: {{"response": "That's not quite right. The correct answer is B. Individuals with a fixed mindset often avoid challenges because they see failure as a negative reflection of their unchangeable intelligence or talent. Don't worry, these concepts can be tricky. Let's keep going! Here is your next question: [next question]", "quiz_active": true, "question_id": 2, "user_score": 1}}
            

            ... (and so on) ...

            
            (After evaluating Q5) -> Output: {{"response": "you got 4 out of 5 correct answers. Great job!. Would you like to take another quiz?", "quiz_active": false, "question_id": 5, "user_score": 4}}


            Context You Will Be Provided With (RAG, History, etc.):


            questions:
            {questions}
            
            Student's answer: {query}"""



        return prompt
        
    
    from app.api.setup_db import get_top_5_content, AsyncSession


    def parse_ai_response(response_text):
        try:
            # Clean the response - remove code block markers
            cleaned_response = re.sub(r'```json\s*|\s*```', '', response_text).strip()

            # Try to parse as JSON
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            try:
                # Try to extract JSON content if there are other issues
                json_match = re.search(r'\{[\s\S]*\}', cleaned_response)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise ValueError("No valid JSON found")
            except:
                # Fallback response
                return {
                    "answer": "Hello! I'm your AI tutor. How can I help you learn today?",
                    "wants_quiz": False,
                    "spoken_language": "english",
                    "quiz": []
                }
        

    async def ask_question(self, question: str, summary: str = None, similar_past_convo: Any = None, history: Any = None, language: str = None, difficulty: str = 'easy', quiz_active: bool = False, questions: Any = None, db: AsyncSession = None) -> str:
        """Ask a question to the AI tutor"""
        
        try:
            # Get query embedding
            logger.info(f"🔍 Processing question: '{question}...'")


            logger.info(f"📚 Searching knowledge base for relevant content...")
            relevant_chunks = await get_top_5_content(question, db)
            
            logger.info(f"✅ Retrieved {len(relevant_chunks)} chunks from knowledge base:")
            contents = ''
            
            for i, chunk_data in enumerate(relevant_chunks):
                print(i, chunk_data)
                content = chunk_data['content']
                contents = contents + content + " ...\n\n "
            
            # Create conversation history for this student
            
            if quiz_active:
                prompt = self._create_quiz_prompt(query=question, relevant_chunks=str(contents), summary=summary, history=history, language=language, difficulty=difficulty, questions=questions)
            else:
                prompt = self._create_tutor_prompt(query=question, summary=summary, similar_convo=similar_past_convo, relevant_chunks=contents, history=history, language=language, difficulty=difficulty)
            # Generate response using the appropriate AI service
            logger.info("🤖 Generating AI tutor response...")
            logger.info(f"🤖 Using {'Bedrock' if self.use_bedrock else 'Gemini'} for AI tutoring")
            
            if self.use_bedrock:
                answer = self.bedrock.generate_content(prompt)
            else:
                response = self.gemini_model.generate_content(prompt)
                answer = response.text

            # Log response summary
            logger.info(f"🎯 Response generated successfully!")

            

            return answer
            
        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            return "I apologize, but I Can't process your request right now. Please try again later",
                
            
tutor = AITutor()