"""
Enhanced AI Service for Iframe Widget Flow
Handles AI interactions and quiz functionality
"""

import logging
import os
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

# Quiz service removed

logger = logging.getLogger(__name__)


class AIService:
    """Enhanced AI service with quiz functionality"""
    
    def __init__(self):
        """Initialize AI service"""
        logger.info("AI service initialized with quiz functionality")
        
        # Basic configuration
        self.default_language = "en"
        self.supported_languages = ["en", "id"]
        
        # Quiz functionality removed
    
    def generate_response(self, message: str, context_docs: List[Dict[str, Any]] = None, summary: str = None, similar_past_convo: Any = None, history: Any = None, language: str = None, difficulty: str = 'easy', quiz_active: bool = False, questions: Any = None) -> Dict[str, Any]:
        """Generate AI response with quiz support"""
        try:
            logger.info(f"Generating AI response for message: {message[:50]}...")
            logger.info(f"🔍 Message: '{message}', Language: {language}")
            
            # Regular AI response (quiz functionality removed)
            if quiz_active:
                response = self._build_quiz_response(message, context_docs=context_docs, summary=summary, questions=questions, history=history, language=language, difficulty=difficulty)
            else:
                response = self._generate_regular_response(message, context_docs=context_docs, summary=summary, similar_past_convo=similar_past_convo, history=history, language=language, difficulty=difficulty)

            logger.info(f"AI Response: {response.text}")
            return response.text

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return "{ 'answer': 'Sorry, I Could not process your request at this time. Please try again later.', 'wants_quiz': False, 'spoken_language': english, 'quiz': [] }"
    

    
    def _generate_regular_response(self, message: str, context_docs: List[Dict[str, Any]], summary: str, similar_past_convo: Any, history: Any, language: str, difficulty: str) -> Dict[str, Any]:
        """Generate context-aware AI response using conversation memory and course content"""
        try:
            # Get conversation history for context
            if len(history) > 3:
                history = history[-3:]

        
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
                2. **Content Accuracy**: Base responses strictly on provided course material, connecting concepts to real-world applications
                3. **Context Utilization**: Always incorporate conversation context for personalized responses
                5. **Conciseness**: Keep responses brief yet comprehensive
                6. **Tutoring Approach**: Be supportive, encouraging, and provide step-by-step explanations for complex concepts
                7. **Error Handling**: Never mention inability to find information or system errors
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
    
   



# Global instance
ai_service = AIService() 