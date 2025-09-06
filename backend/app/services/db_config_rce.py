"""
Database configuration and connection management for AI Tutor RAG pipeline
Handles PostgreSQL connections with pgvector extension support
"""

import os
import logging
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_connection_string() -> str:
    """Get PostgreSQL connection string from environment variables"""
    return f"postgresql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"


def get_database_connection() -> Optional[psycopg2.extensions.connection]:
    """Get a database connection with pgvector support"""
    try:
        connection = psycopg2.connect(
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            cursor_factory=RealDictCursor
        )
        
        # Enable pgvector extension
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            connection.commit()
            
        logger.info("✅ Database connection established with pgvector support")
        return connection
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return None


def test_connection() -> bool:
    """Test database connection and pgvector extension"""
    try:
        connection = get_database_connection()
        if connection:
            with connection.cursor() as cursor:
                # Test basic connection
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                logger.info(f"✅ PostgreSQL version: {version['version']}")
                
                # Test pgvector extension
                cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
                pgvector = cursor.fetchone()
                if pgvector:
                    logger.info("✅ pgvector extension is available")
                else:
                    logger.warning("⚠️ pgvector extension not found")
                
                # Test if course_chunks table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'course_chunks'
                    );
                """)
                table_exists = cursor.fetchone()['exists']
                if table_exists:
                    logger.info("✅ course_chunks table found")
                else:
                    logger.warning("⚠️ course_chunks table not found")
                
            connection.close()
            return True
            
    except Exception as e:
        logger.error(f"❌ Connection test failed: {e}")
        return False
    
    return False


def create_course_chunks_table():
    """Create the course_chunks table if it doesn't exist"""
    try:
        connection = get_database_connection()
        if not connection:
            return False
            
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS course_chunks (
                    id SERIAL PRIMARY KEY,
                    course_id VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    chunk_type VARCHAR(50),
                    topic VARCHAR(100),
                    module VARCHAR(100),
                    module_item_id VARCHAR(50),
                    page_slug VARCHAR(100),
                    embedding vector(112),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_course_chunks_course_id 
                ON course_chunks(course_id);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_course_chunks_chunk_type 
                ON course_chunks(chunk_type);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_course_chunks_topic 
                ON course_chunks(topic);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_course_chunks_embedding 
                ON course_chunks USING ivfflat (embedding vector_cosine_ops);
            """)
            
            connection.commit()
            logger.info("✅ course_chunks table created successfully")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to create course_chunks table: {e}")
        return False
    finally:
        if connection:
            connection.close()


def get_course_chunks_count(course_id: str) -> int:
    """Get the count of chunks for a specific course"""
    try:
        connection = get_database_connection()
        if not connection:
            return 0
            
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM course_chunks 
                WHERE course_id = %s
            """, (course_id,))
            
            result = cursor.fetchone()
            count = result['count'] if result else 0
            
        connection.close()
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed to get course chunks count: {e}")
        return 0


def get_course_chunks_metadata(course_id: str) -> list:
    """Get metadata about chunks for a specific course"""
    try:
        connection = get_database_connection()
        if not connection:
            return []
            
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    chunk_type,
                    topic,
                    module,
                    COUNT(*) as count
                FROM course_chunks 
                WHERE course_id = %s
                GROUP BY chunk_type, topic, module
                ORDER BY chunk_type, topic, module
            """, (course_id,))
            
            results = cursor.fetchall()
            metadata = [dict(row) for row in results]
            
        connection.close()
        return metadata
        
    except Exception as e:
        logger.error(f"❌ Failed to get course chunks metadata: {e}")
        return [] 