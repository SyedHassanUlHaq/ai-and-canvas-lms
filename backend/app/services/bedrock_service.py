"""
AWS Bedrock Service for AI Tutor Widget
Replaces Google Vertex AI Gemini with AWS Bedrock models
"""

import logging
import boto3
import json
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class BedrockService:
    """AWS Bedrock service for AI interactions"""
    
    def __init__(self, region_name: str = None, model_id: str = None):
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        self.model_id = model_id or os.getenv('BEDROCK_MODEL', 'none')
        
        # Get AWS credentials from environment
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        if not self.aws_access_key or not self.aws_secret_key:
            raise ValueError("AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
        
        # Initialize Bedrock client
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key
        )
        
        # Available models mapping
        self.available_models = {
            # 'claude_sonnet': 'anthropic.claude-3-sonnet-20240229-v1:0'
            'claude_haiku': 'anthropic.claude-sonnet-4-20250514-v1:0'
            # 'claude_opus': 'anthropic.claude-3-opus-20240229-v1:0',
            # 'titan_text': 'amazon.titan-text-express-v1',
            # 'llama2_13b': 'meta.llama2-13b-chat-v1',
            # 'llama2_70b': 'meta.llama2-70b-chat-v1'
        }
        
        logger.info(f"✅ Bedrock service initialized with model: {self.model_id}")
        
    def generate_content(self, prompt: str, model_id: str = None, 
                        max_tokens: int = 10000, temperature: float = 0.3, is_quiz_active: bool = False) -> str:
        """Generate content using AWS Bedrock"""
        try:
            model_id = model_id or self.model_id
            
            if 'claude' in model_id:
                return self._generate_claude_content(prompt, model_id, max_tokens, temperature, is_quiz_active)
            # elif 'titan' in model_id:
            #     return self._generate_titan_content(prompt, model_id, max_tokens, temperature)
            # elif 'llama' in model_id:
            #     return self._generate_llama_content(prompt, model_id, max_tokens, temperature)
            else:
                raise ValueError(f"Unsupported model: {model_id}")
                
        except Exception as e:
            logger.error(f"Error generating content with Bedrock: {e}")
            raise
    
    def _generate_claude_content(self, prompt: str, model_id: str, 
                                max_tokens: int, temperature: float, is_quiz_active) -> str:
        """Generate content using Claude models"""
        try:
            if not is_quiz_active:
                schema = {
          "$schema": "https://json-schema.org/draft/2020-12/schema",
          "description": "Schema for quiz responses with metadata and a list of quiz questions",
          "type": "object",
          "properties": {
            "answer": {
              "type": "string",
              "description": "The assistant's response to the user, including quiz introduction or instructions."
            },
            "wants_quiz": {
              "type": "boolean",
              "description": "Indicates if the user wants to proceed with a quiz."
            },
            "spoken_language": {
              "type": "string",
              "description": "The language in which the quiz will be presented."
            },
            "quiz": {
              "type": "array",
              "description": "A list of quiz questions.",
              "items": {
                "type": "object",
                "properties": {
                  "question_number": {
                    "type": "integer",
                    "description": "The number of the question in the sequence."
                  },
                  "difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard"],
                    "description": "The difficulty level of the question."
                  },
                  "question_type": {
                    "type": "string",
                    "enum": ["true_false", "multiple_choice"],
                    "description": "The type of question (true/false or multiple choice)."
                  },
                  "question_text": {
                    "type": "string",
                    "description": "The text of the quiz question."
                  },
                  "options": {
                    "type": "object",
                    "description": "The answer options for the question, keyed by letter.",
                    "patternProperties": {
                      "^[A-Z]$": {
                        "type": "string"
                      }
                    },
                    "minProperties": 1
                  },
                  "expected_answer": {
                    "type": "string",
                    "description": "The correct answer key (e.g., 'A')."
                  },
                  "explanation": {
                    "type": "string",
                    "description": "Explanation of the correct answer."
                  }
                },
                "required": [
                  "question_number",
                  "difficulty",
                  "question_type",
                  "question_text",
                  "options",
                  "expected_answer",
                  "explanation"
                ]
              }
            }
          },
          "required": ["answer", "wants_quiz", "spoken_language", "quiz"]
        }
            else:   
                schema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "description": "Schema for quiz response evaluation and progression",
  "type": "object",
  "properties": {
    "response": {
      "type": "string",
      "description": "Tutor’s feedback message. Must include correctness evaluation, explanation, and (if applicable) the next question."
    },
    "quiz_active": {
      "type": "boolean",
      "description": "True if the quiz is still ongoing with questions left. False if the quiz has ended."
    },
    "question_id": {
      "type": "integer",
      "minimum": 1,
      "description": "The ID of the question just handled. Remains the same until moving to the next question."
    },
    "user_score": {
      "type": "integer",
      "minimum": 0,
      "maximum": 5,
      "description": "The user’s cumulative score so far, based on correct answers."
    }
  },
  "required": ["response", "quiz_active", "question_id", "user_score"],
  "additionalProperties": 'false'
}


            input_data = {
  "message": "Can you quiz me on design principles?",
  "summary": "We’ve been learning about Design Thinking stages.",
  "similar_past_convo": "Previously, the student asked about prototyping vs testing.",
  "history": "Student asked: 'What is empathy in design?' — Tutor explained empathy in user research.",
  "language": "english",
  "difficulty": "medium",
  "context_docs": "Design Thinking has 5 stages: Empathize, Define, Ideate, Prototype, Test."
            }
            
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                # "response_format": {"type": "json"},
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "text", "text": json.dumps(schema)}
                            # {"type": "text", "text": json.dumps(input_data)}
                        ]
                    }
                ],
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
            )
            
            response_body = json.loads(response['body'].read())
            logger.info(f"Response body: {response_body}")
            return response_body['content'][0]['text']
            
        except ClientError as e:
            logger.error(f"Claude generation error: {e}")
            raise
    
    # def _generate_titan_content(self, prompt: str, model_id: str, 
    #                            max_tokens: int, temperature: float) -> str:
    #     """Generate content using Amazon Titan models"""
    #     try:
    #         body = {
    #             "inputText": prompt,
    #             "textGenerationConfig": {
    #                 "maxTokenCount": max_tokens,
    #                 "temperature": temperature,
    #                 "topP": 0.9
    #             }
    #         }
            
    #         response = self.bedrock_client.invoke_model(
    #             modelId=model_id,
    #             body=json.dumps(body),
    #             contentType="application/json"
    #         )
            
    #         response_body = json.loads(response['body'].read())
    #         return response_body['results'][0]['outputText']
            
    #     except ClientError as e:
    #         logger.error(f"Titan generation error: {e}")
    #         raise
    
    # def _generate_llama_content(self, prompt: str, model_id: str, 
    #                            max_tokens: int, temperature: float) -> str:
    #     """Generate content using Llama models"""
    #     try:
    #         body = {
    #             "prompt": prompt,
    #             "max_gen_len": max_tokens,
    #             "temperature": temperature,
    #             "top_p": 0.9
    #         }
            
    #         response = self.bedrock_client.invoke_model(
    #             modelId=model_id,
    #             body=json.dumps(body),
    #             contentType="application/json"
    #         )
            
    #         response_body = json.loads(response['body'].read())
    #         return response_body['generation']
            
    #     except ClientError as e:
    #         logger.error(f"Llama generation error: {e}")
    #         raise
    
    # def list_available_models(self) -> List[str]:
        # """List available models"""
        # return list(self.available_models.values())
    
    # def get_model_info(self, model_name: str) -> str:
    #     """Get model ID by name"""
    #     return self.available_models.get(model_name, self.model_id)

# Global instance
bedrock_service = BedrockService()
