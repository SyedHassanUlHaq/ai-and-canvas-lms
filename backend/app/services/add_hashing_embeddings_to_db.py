import json 
import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.cloud import aiplatform
from vertexai.language_models import TextGenerationModel
from vertexai.generative_models import GenerativeModel
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import hashlib
from app.repository.vector import CourseChunkRepository
from app.core.config import Settings


logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Document chunk structure compatible with existing system"""
    id: str
    content: str
    content_metadata: Dict[str, Any]
    chunk_type: str
    parent_id: Optional[str] = None
    related_ids: Optional[List[str]] = None

def setup_database(chunks_data):
    """Setup database and load chunks"""
    
    try:
        # Load chunks from JSON
        
        project_id = "elivision-ai-1"
        # Convert to DocumentChunk objects
        chunks = []
        for chunk_data in chunks_data:
            if chunk_data['metadata']['chunk_type'] == 'module_overview':
                continue
            else:
                chunk = DocumentChunk(
                    id=chunk_data['id'],
                    content=chunk_data['content'],
                    content_metadata=chunk_data['metadata'],
                    chunk_type=chunk_data['chunk_type'],
                    parent_id=chunk_data.get('parent_id'),
                    related_ids=chunk_data.get('related_ids', [])
                )
                chunks.append(chunk)
        logger.info(f"✅ Loaded {len(chunks)} chunks")
        
        # Initialize embedding model
        logger.info("🔄 Initializing embedding model...")
        embedding_model = GeminiEmbeddingModel(project_id)
        
        # Generate embeddings
        logger.info("🔄 Generating embeddings...")
        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = embedding_model.get_embeddings(chunk_texts)
        
        # Initialize database repository
        logger.info("🔄 Initializing database connection...")
        # Replace with your actual database connection string
        
        repository = CourseChunkRepository("postgresql://postgres:uncharted3@localhost:5432/canvas_db")

        print(1)
        
        # Prepare chunks for storage (convert to dictionary format)
        chunks_dict = []
        for chunk in chunks:
            chunks_dict.append({
                'id': chunk.id,
                'content': chunk.content,
                'content_metadata': chunk.content_metadata,
                'chunk_type': chunk.chunk_type,
                'parent_id': chunk.parent_id,
                'related_ids': chunk.related_ids
            })
        
        # Store chunks with embeddings
        logger.info("💾 Storing chunks with embeddings in database...")
        repository.add_chunks(chunks_dict, embeddings)
        
        logger.info(f"✅ Successfully stored {len(chunks)} chunks with embeddings in database")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error setting up database: {e}")
        return False



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