"""
Widget AI Service for AI Tutor Widget
Uses either AWS Bedrock Claude or Google Vertex AI Gemini based on USE_BEDROCK environment variable
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Conditional imports based on USE_BEDROCK setting
USE_BEDROCK = os.getenv('USE_BEDROCK').lower() == 'true'

if USE_BEDROCK:
    from .bedrock_service import bedrock_service
    logger = logging.getLogger(__name__)
    logger.info("🤖 Using AWS Bedrock Claude for AI generation")
else:
    import google.auth
    from google.cloud import aiplatform
    from vertexai.generative_models import GenerativeModel
    logger = logging.getLogger(__name__)
    logger.info("🤖 Using Google Vertex AI Gemini for AI generation")


class WidgetAIService:
    """AI service specifically for the widget using either Bedrock Claude or Gemini based on USE_BEDROCK setting"""
    
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

    def _setup_credentials(self):
        """Setup Google Cloud credentials"""
        try:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.credentials_path
            credentials, project = google.auth.default()
            logger.info(f"✅ Successfully authenticated with project: {project}")
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            raise
        
        # Quiz functionality removed
    
    def generate_response(self, message: str, context_docs: List[Dict[str, Any]] = None, summary: str = None, similar_past_convo: Any = None, history: Any = None, language: str = None, difficulty: str = 'easy', quiz_active: bool = False, questions: Any = None) -> Dict[str, Any]:
        """Generate AI response with quiz support using either Bedrock or Gemini"""
        try:
            logger.info(f"Generating AI response for message: {message[:50]}...")
            logger.info(f"🔍 Message: '{message}', Language: {language}")
            logger.info(f"🤖 Using {'Bedrock' if self.use_bedrock else 'Gemini'} for AI generation")
            
            # Regular AI response (quiz functionality removed)
            if quiz_active:
                prompt = self._build_quiz_response(message, context_docs=context_docs, summary=summary, questions=questions, history=history, language=language, difficulty=difficulty)
            else:
                prompt = self._generate_regular_response(message, context_docs=context_docs, summary=summary, similar_past_convo=similar_past_convo, history=history, language=language, difficulty=difficulty)

            # Generate response using the appropriate AI service
            if self.use_bedrock:
                answer = self.bedrock.generate_content(prompt, is_quiz_active=quiz_active)
            else:
                response = self.gemini_model.generate_content(prompt)
                answer = response.text
                
            # logger.info(f"AI Response: {answer}")
            return answer

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return "{ 'answer': 'Sorry, I Could not process your request at this time. Please try again later.', 'wants_quiz': false, 'spoken_language': english, 'quiz': [] }"
    

    
    def _generate_regular_response(self, message: str, context_docs: List[Dict[str, Any]], summary: str, similar_past_convo: Any, history: Any, language: str, difficulty: str) -> Dict[str, Any]:
        """Generate context-aware AI response using conversation memory and course content"""
        try:
            # Get conversation history for context
            if len(history) > 3:
                history = history[-3:]

            print("CONTEXT DOCS: ", context_docs)
        # Create the comprehensive prompt
            prompt = f"""
                You are an expert AI tutor for a course on Design Thinking, Psychology, and Leadership Development. 
                Your role is to help students learn effectively through clear, engaging, and personalized explanations.

                ### CONTEXT
                - Conversation Summary: {summary}
                - Relevant Previous Information: {similar_past_convo}
                - Recent Messages: {history}
                - Student's Preferred Language: {language}
                - Quiz Difficulty Level: {difficulty}

                ### RELEVANT COURSE MATERIAL:
                {context_docs}

                ### INSTRUCTIONS:
                1. **Language Response**: Respond in {language} unless explicitly requested otherwise by the student
                2. **Content Accuracy**: Greet the students and base responses strictly on provided course material and the youtube transcript (if available), connecting concepts to real-world applications
                3. **Context Utilization**: Always incorporate conversation context for personalized responses
                4. **Out of context Questions**: for every question, check if the query is related to the RELEVANT COURSE MATERIAL. if it s not, then tell the respond with "Your question is not related to our current topic. If you have any queries on the current topic, Let me know and I'll be happy to help".
                5. **Conciseness**: Keep responses brief yet comprehensive
                6. **Tutoring Approach**: Be supportive, encouraging, and provide step-by-step explanations for complex concepts
                7. **Error Handling**: Never mention inability to find information or system errors
                9. **Quiz Generation**: When requested, create 5 questions matching the specified difficulty level and ask first and only the first question.
                10. **CRITICAL QUIZ FORMATTING**: 
                    - For MEDIUM difficulty: ALWAYS include the question text AND all 4 multiple choice options (A, B, C, D) in the "answer" field
                    - Format: "Question text?\nA: Option 1\nB: Option 2\nC: Option 3\nD: Option 4"
                11. **Structured Output**: Always respond with valid JSON format
                12. **NEVER ADD `//n` in JSON STRINGS, REPLACE THEM WITH `/n`**
                13. **ALWAYS REPLACE `//n` with `/n`**

                ### QUIZ DIFFICULTY GUIDELINES:
                - **Easy**: ALWAYS true/false questions testing basic recall
                - **Medium**: ALWAYS multiple choice questions (4 options A-D) testing understanding and application
                - **Hard**: ALWAYS short answer questions requiring concept explanation and critical thinking
                
                **CRITICAL**: Follow difficulty guidelines EXACTLY. Medium difficulty MUST be multiple choice with 4 options.

                ### CRITICAL: Your response must always be in the specified JSON format,  NO ADDITIONAL TEXT. NUMBER OF QUESTIONS MUST ALWAYS BE 5 IF THE USER WANTS QUIZ

                ### STRICT FORMATTING RULES: 
                    - NO code block markers (no ```json or ```)
                    - NO text before or after the JSON
                    - NO explanations or additional content
                    - ONLY the raw JSON object
                    - Make the answers properly formatted with \\n for new lines, and use bullet points where appropriate, but keep it concise.



                ### RESPONSE FORMAT:
                Always return valid JSON with this structure:
                Schema:
                {{
                    "answer": "Your educational response here", 
                    "wants_quiz": false,
                    "spoken_language": "language_code",
                    "quiz": []
                }}

                Quiz questions should follow this format:
                Schema:
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
                        {{
                            "question_number": 2,
                            "difficulty": "easy",
                            "question_type": "true_false",
                            "question_text": "The Define stage comes before the Ideate stage in Design Thinking.",
                            "options": {{"A": "True", "B": "False"}},
                            "expected_answer": "A",
                            "explanation": "The Design Thinking process follows: Empathize → Define → Ideate → Prototype → Test."
                        }},
                        {{
                            "question_number": 3,
                            "difficulty": "easy",
                            "question_type": "true_false",
                            "question_text": "Prototyping is the final stage of Design Thinking.",
                            "options": {{"A": "True", "B": "False"}},
                            "expected_answer": "B",
                            "explanation": "Testing is the final stage. Prototyping comes before testing."
                        }},
                        {{
                            "question_number": 4,
                            "difficulty": "easy",
                            "question_type": "true_false",
                            "question_text": "Empathy involves understanding user emotions and experiences.",
                            "options": {{"A": "True", "B": "False"}},
                            "expected_answer": "A",
                            "explanation": "Empathy is about understanding users' feelings, thoughts, and experiences."
                        }},
                        {{
                            "question_number": 5,
                            "difficulty": "easy",
                            "question_type": "true_false",
                            "question_text": "Design Thinking is only used for product design.",
                            "options": {{"A": "True", "B": "False"}},
                            "expected_answer": "B",
                            "explanation": "Design Thinking can be applied to various fields including business, education, and social innovation."
                        }}
                    ]
                }}

                4. **Quiz Request (Medium)**:
                Student: "Can you quiz me on design principles?"
                Response:
                {{
                    "answer": "Of course. I've designed the questions for you. Here's the first one: What is the primary purpose of a low-fidelity prototype?\\nA: To create a polished final product\\nB: To test ideas quickly without significant investment\\nC: To impress stakeholders with detailed design\\nD: To replace the need for user testing",
                    "wants_quiz": true,
                    "spoken_language": "english",
                    "quiz": [
                        {{
                            "question_number": 1,
                            "difficulty": "medium",
                            "question_type": "multiple_choice",
                            "question_text": "What is the primary purpose of a low-fidelity prototype?",
                            "options": {{
                                "A": "To create a polished final product",
                                "B": "To test ideas quickly without significant investment",
                                "C": "To impress stakeholders with detailed design",
                                "D": "To replace the need for user testing"
                            }},
                            "expected_answer": "B",
                            "explanation": "Low-fidelity prototypes are quick, low-cost representations used to test core concepts without investing significant time or resources."
                        }},
                        {{
                            "question_number": 2,
                            "difficulty": "medium",
                            "question_type": "multiple_choice",
                            "question_text": "Which of the following is an example of a high-fidelity prototype?",
                            "options": {{
                                "A": "A hand-drawn sketch on a napkin",
                                "B": "A paper model of a mobile app screen",
                                "C": "A clickable, interactive model created in Figma",
                                "D": "A workflow diagram on a whiteboard"
                            }},
                            "expected_answer": "C",
                            "explanation": "High-fidelity prototypes are detailed, interactive models that closely resemble the final product."
                        }},
                        {{
                            "question_number": 3,
                            "difficulty": "medium",
                            "question_type": "multiple_choice",
                            "question_text": "What is the main goal of the Empathize stage in Design Thinking?",
                            "options": {{
                                "A": "To generate as many ideas as possible",
                                "B": "To understand the user's needs and experiences",
                                "C": "To create the final solution",
                                "D": "To test the prototype with users"
                            }},
                            "expected_answer": "B",
                            "explanation": "The Empathize stage focuses on gaining insight into users' experiences, emotions, and needs."
                        }},
                        {{
                            "question_number": 4,
                            "difficulty": "medium",
                            "question_type": "multiple_choice",
                            "question_text": "Which stage of Design Thinking involves narrowing down ideas to the most promising ones?",
                            "options": {{
                                "A": "Empathize",
                                "B": "Define",
                                "C": "Ideate",
                                "D": "Prototype"
                            }},
                            "expected_answer": "C",
                            "explanation": "The Ideate stage involves generating many ideas and then selecting the most promising ones for prototyping."
                        }},
                        {{
                            "question_number": 5,
                            "difficulty": "medium",
                            "question_type": "multiple_choice",
                            "question_text": "What is the primary benefit of iterative prototyping?",
                            "options": {{
                                "A": "It saves money on materials",
                                "B": "It allows for continuous improvement based on feedback",
                                "C": "It reduces the need for user research",
                                "D": "It speeds up the final production process"
                            }},
                            "expected_answer": "B",
                            "explanation": "Iterative prototyping allows teams to continuously refine solutions based on user feedback and testing results."
                        }}
                    ]
                }}

                5. **Quiz Request (Hard)**:
                Student: "Can you quiz me on design principles?"
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
                        {{
                            "question_number": 2,
                            "difficulty": "hard",
                            "question_type": "short_answer",
                            "question_text": "Explain the difference between a problem statement and a solution statement in the Define stage.",
                            "expected_answer": "A problem statement describes what needs to be solved, while a solution statement describes how to solve it.",
                            "explanation": "Problem statements focus on the issue, solution statements focus on the approach."
                        }},
                        {{
                            "question_number": 3,
                            "difficulty": "hard",
                            "question_type": "short_answer",
                            "question_text": "What are the key characteristics of effective brainstorming in the Ideate stage?",
                            "expected_answer": "Encourage wild ideas, defer judgment, build on others' ideas, and aim for quantity over quality initially.",
                            "explanation": "Effective brainstorming creates a safe space for creative thinking without immediate criticism."
                        }},
                        {{
                            "question_number": 4,
                            "difficulty": "hard",
                            "question_type": "short_answer",
                            "question_text": "Describe how you would conduct user testing for a mobile app prototype.",
                            "expected_answer": "Set clear objectives, recruit representative users, create realistic scenarios, observe behavior, and collect both quantitative and qualitative feedback.",
                            "explanation": "User testing should be systematic, objective, and focused on real user behavior."
                        }},
                        {{
                            "question_number": 5,
                            "difficulty": "hard",
                            "question_type": "short_answer",
                            "question_text": "How does Design Thinking contribute to innovation in organizations?",
                            "expected_answer": "It provides a human-centered approach to problem-solving, encourages collaboration, and enables rapid iteration to find breakthrough solutions.",
                            "explanation": "Design Thinking drives innovation by focusing on user needs and enabling creative problem-solving processes."
                        }}
                    ]
                }}

                ### CRITICAL REMINDER FOR MEDIUM DIFFICULTY QUIZZES:
                If difficulty is "medium" and wants_quiz is true, your "answer" field MUST include:
                1. The introduction text
                2. The question text
                3. ALL 4 multiple choice options (A, B, C, D) with \\n line breaks
                
                Example format for medium difficulty:
                "answer": "Of course. Here's the first one: [Question text]?\\nA: [Option 1]\\nB: [Option 2]\\nC: [Option 3]\\nD: [Option 4]"

                ### CURRENT STUDENT QUERY: {message}

                Provide a concise, helpful response that demonstrates your expertise as an AI tutor. Use bullet points for readability when appropriate.
                """

            return prompt
            

        except Exception as e:
            logger.error(f"Error generating regular response: {e}")
            return self._generate_error_response(str(e), language)
    
    def _build_quiz_response(self, message: str, context_docs: List[Dict[str, Any]], summary: str, questions: Any, history: Any, language: str, difficulty: str) -> str:
        """Build response using relevant course content"""
        try:
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
                {context_docs}


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

                Student's answer: {message}"""



            return prompt
            
        except Exception as e:
            logger.error(f"Error building contextual response: {e}")
            return self._build_general_response(message, language)


# Create global instance
widget_ai_service = WidgetAIService() 