import numpy as np
import warnings

# def patched_array(obj, copy=None, **kwargs):
#     if copy is False:
#         warnings.warn("copy=False is deprecated in NumPy 2.0, using np.asarray instead")
#         return np.asarray(obj, **kwargs)
#     return original_array(obj, copy=copy, **kwargs)

# np.array = patched_array

import fasttext

model = fasttext.load_model("lid.176.bin")


def detect_language(text: str) -> str | None:
    """
    Detect if text is English or Indonesian.
    Returns 'english', 'indonesian', or None.
    """
    print("Detecting language...", text)
    # Normalize text
    IGNORE = {"hi", "hello", "yes"}
    cleaned = text.strip().lower()

    # Check ignored words
    if cleaned in IGNORE:
        return None

    # Predict language
    labels, probs = model.predict(text, k=3)
    print(f"Detected labels: {labels} with probabilities {probs}")

    for label, prob in zip(labels, probs):
        if label == "__label__en":
            return "english"
        elif label in ("__label__id", "__label__min"):  # treat Minangkabau as Indonesian
            return "indonesian"

    return None



##################################################################################################################


#!/usr/bin/env python3
"""
Canvas to PostgreSQL Data Storage Script with YouTube Transcription
Fetches Canvas course data and stores it in PostgreSQL database
Automatically detects and transcribes YouTube videos in page content
"""

import requests
import re
import html
import psycopg2
import subprocess
import whisper
import os
import tempfile
from typing import Dict, List, Any, Optional
import logging
from app.services.db_config_rce import get_connection_string

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# Database Configuration
# Parse connection string to get individual components
def parse_connection_string(conn_string):
    """Parse PostgreSQL connection string into components"""
    # Remove postgresql:// prefix if present
    if conn_string.startswith('postgresql://'):
        conn_string = conn_string[13:]
    
    # Parse components
    parts = conn_string.split('@')
    if len(parts) == 2:
        user_pass, host_port_db = parts
        user, password = user_pass.split(':')
        host_port, database = host_port_db.split('/')
        host, port = host_port.split(':')
        
        return {
            'host': host,
            'port': int(port),
            'database': database,
            'user': user,
            'password': password
        }
    else:
        # Fallback to default values
        return {
            'host': 'localhost',
            'port': 5432,
            'database': 'ai_tutor_db',
            'user': 'ai_tutor_user',
            'password': 'ai_tutor_password'
        }

# Get database configuration from existing config
try:
    conn_string = get_connection_string()
    DB_CONFIG = parse_connection_string(conn_string)
    print(f"✅ Database config loaded from db_config.py")
except Exception as e:
    print(f"⚠️ Warning: Could not load db_config.py, using defaults: {e}")
    DB_CONFIG = {
        'host': 'localhost',
        'port': 5432,
        'database': 'ai_tutor_db',
        'user': 'ai_tutor_user',
        'password': 'ai_tutor_password'
    }

# API Headers
headers = {
    'Authorization': f'Bearer {os.getenv("CANVAS_API_TOKEN")}',
    'Content-Type': 'application/json'
}

class CanvasDataStore:
    """Class to fetch Canvas data and store it in PostgreSQL with YouTube transcription"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self.connection = None
        self.cursor = None
        self.whisper_model = None
        
    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.connection = psycopg2.connect(**self.db_config)
            self.cursor = self.connection.cursor()
            logger.info("✅ Connected to PostgreSQL database")
            
            # Ensure pages table has yt_transcript column
            self._ensure_yt_transcript_column()
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def _ensure_yt_transcript_column(self):
        """Ensure the pages table has yt_transcript column"""
        try:
            self.cursor.execute("""
                ALTER TABLE pages 
                ADD COLUMN IF NOT EXISTS yt_transcript TEXT
            """)
            self.connection.commit()
            logger.info("✅ Ensured yt_transcript column exists in pages table")
        except Exception as e:
            logger.error(f"❌ Error adding yt_transcript column: {e}")
    
    def close_db(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            logger.info("🔌 Database connection closed")

    def get_all_courses(self) -> List[int]:
        """Fetch all courses from Canvas and return their IDs"""
        try:
            response = requests.get(f"{os.getenv("CANVAS_URL")}/api/v1/courses", headers=headers)
            response.raise_for_status()
            courses = response.json()
            return [course['id'] for course in courses]
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching courses: {e}")
            return [] 
            
    def fetch_canvas_data(self, endpoint: str, course_id) -> Optional[List[Dict]]:
        """Fetch data from Canvas API endpoint"""
        url = f"{os.getenv("CANVAS_URL")}/api/v1/courses/{course_id}/{endpoint}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info(f"✅ Fetched {len(data) if isinstance(data, list) else 1} items from {endpoint}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching {endpoint}: {e}")
            return None
    
    def fetch_module_items(self, module_id: int, course_id) -> Optional[List[Dict]]:
        """Fetch items for a specific module"""
        url = f"{os.getenv("CANVAS_URL")}/api/v1/courses/{course_id}/modules/{module_id}/items"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info(f"✅ Fetched {len(data)} items for module {module_id}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching module items for module {module_id}: {e}")
            return None
    
    def fetch_page_content(self, page_url: str, course_id) -> Optional[Dict]:
        """Fetch the body content of a specific page"""
        url = f"{os.getenv("CANVAS_URL")}/api/v1/courses/{course_id}/pages/{page_url}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info(f"✅ Fetched page content for {page_url}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching page content for {page_url}: {e}")
            return None
    
    def extract_youtube_urls(self, html_content: str) -> List[str]:
        """Extract YouTube URLs from HTML content"""
        if not html_content:
            return []
        
        youtube_urls = []
        
        # Pattern for YouTube embed URLs
        embed_pattern = r'<iframe[^>]*src="([^"]*youtube\.com/embed/[^"]*)"[^>]*>'
        embed_matches = re.findall(embed_pattern, html_content, re.IGNORECASE)
        
        # Pattern for direct YouTube URLs
        direct_pattern = r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)'
        direct_matches = re.findall(direct_pattern, html_content, re.IGNORECASE)
        
        # Convert embed URLs to watch URLs
        for embed_url in embed_matches:
            video_id_match = re.search(r'/embed/([a-zA-Z0-9_-]+)', embed_url)
            if video_id_match:
                video_id = video_id_match.group(1)
                youtube_urls.append(f"https://www.youtube.com/watch?v={video_id}")
        
        # Add direct URLs
        for video_id in direct_matches:
            youtube_urls.append(f"https://www.youtube.com/watch?v={video_id}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in youtube_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls
    
    def download_audio(self, youtube_url: str, output_file: str = None) -> Optional[str]:
        """Download audio from YouTube video"""
        if not output_file:
            output_file = tempfile.mktemp(suffix=".mp3")
        
        try:
            logger.info(f"🎵 Downloading audio from: {youtube_url}")
            subprocess.run([
                "yt-dlp", "-x", "--audio-format", "mp3", "-o", output_file, youtube_url
            ], check=True, capture_output=True)
            logger.info(f"✅ Audio downloaded to: {output_file}")
            return output_file
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error downloading audio: {e}")
            return None
        except FileNotFoundError:
            logger.error("❌ yt-dlp not found. Please install it: pip install yt-dlp")
            return None
    
    def transcribe_with_whisper(self, audio_file: str) -> Optional[str]:
        """Transcribe audio using Whisper"""
        try:
            if not self.whisper_model:
                logger.info("🔄 Loading Whisper model...")
                self.whisper_model = whisper.load_model("base")
            
            logger.info(f"�� Transcribing audio: {audio_file}")
            result = self.whisper_model.transcribe(audio_file)
            transcript = result["text"].strip()
            logger.info(f"✅ Transcription completed ({len(transcript)} characters)")
            return transcript
        except Exception as e:
            logger.error(f"❌ Error transcribing audio: {e}")
            return None
    
    def transcribe_youtube_video(self, youtube_url: str) -> Optional[str]:
        """Download and transcribe a YouTube video"""
        try:
            # Download audio
            audio_file = self.download_audio(youtube_url)
            if not audio_file:
                return None
            
            # Transcribe audio
            transcript = self.transcribe_with_whisper(audio_file)
            
            # Clean up audio file
            try:
                os.remove(audio_file)
            except:
                pass
            
            return transcript
        except Exception as e:
            logger.error(f"❌ Error transcribing YouTube video {youtube_url}: {e}")
            return None
    
    def clean_html(self, html_content: str) -> str:
        """Clean HTML content and extract readable text, preserving YouTube video references"""
        if not html_content:
            return ""
        
        # Extract YouTube URLs before cleaning
        youtube_urls = self.extract_youtube_urls(html_content)
        
        # Decode HTML entities
        text = html.unescape(html_content)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Add YouTube video references
        if youtube_urls:
            video_refs = []
            for i, url in enumerate(youtube_urls, 1):
                video_refs.append(f"[VIDEO {i}: {url}]")
            text += " " + " ".join(video_refs)
        
        return text
    
    def store_modules(self, modules: List[Dict], course_id) -> bool:
        """Store modules in database and link to course"""
        try:
            for module in modules:
                # Store module itself
                self.cursor.execute("""
                    INSERT INTO modules (id, name, position, published, description, items_count, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        position = EXCLUDED.position,
                        published = EXCLUDED.published,
                        description = EXCLUDED.description,
                        items_count = EXCLUDED.items_count,
                        updated_at = EXCLUDED.updated_at
                """, (
                    module['id'],
                    module['name'],
                    module.get('position'),
                    module.get('published', False),
                    module.get('description'),
                    module.get('items_count', 0),
                    module.get('created_at'),
                    module.get('updated_at')
                ))

                # Store mapping in course_modules
                self.cursor.execute("""
                    INSERT INTO course_modules (course_id, module_id)
                    VALUES (%s, %s)
                    ON CONFLICT (course_id, module_id) DO NOTHING
                """, (
                    course_id,
                    module['id']
                ))

            self.connection.commit()
            logger.info(f"✅ Stored {len(modules)} modules and course-module links in database")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error storing modules: {e}")
            self.connection.rollback()
            return False
    
    def store_module_items(self, module_id: int, items: List[Dict], course_id) -> bool:
        """Store module items in database"""
        try:
            for item in items:
                # Store module item
                self.cursor.execute("""
                    INSERT INTO module_items (id, module_id, title, item_type, position, published, 
                                           content_id, page_url, external_url, completion_requirement, 
                                           created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        item_type = EXCLUDED.item_type,
                        position = EXCLUDED.position,
                        published = EXCLUDED.published,
                        content_id = EXCLUDED.content_id,
                        page_url = EXCLUDED.page_url,
                        external_url = EXCLUDED.external_url,
                        completion_requirement = EXCLUDED.completion_requirement,
                        updated_at = EXCLUDED.updated_at
                """, (
                    item['id'],
                    module_id,
                    item['title'],
                    item['type'],
                    item.get('position'),
                    item.get('published', False),
                    item.get('content_id'),
                    item.get('page_url'),
                    item.get('external_url'),
                    item.get('completion_requirement', {}).get('type'),
                    item.get('created_at'),
                    item.get('updated_at')
                ))
                
                # Store page content for page type items only
                if item['type'].lower() == 'page' and item.get('page_url'):
                    self._store_page_content(item, course_id)
            
            self.connection.commit()
            logger.info(f"✅ Stored {len(items)} module items for module {module_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing module items: {e}")
            self.connection.rollback()
            return False
    
    def _store_page_content(self, item: Dict, course_id):
        """Store page content for page type items with YouTube transcription"""
        try:
            page_content = self.fetch_page_content(item['page_url'], course_id)
            if not page_content:
                return
            
            # Extract YouTube URLs from page content
            youtube_urls = self.extract_youtube_urls(page_content.get('body', ''))
            
            # Transcribe YouTube videos if found
            yt_transcript = None
            if youtube_urls:
                logger.info(f"�� Found {len(youtube_urls)} YouTube video(s) in page: {item['title']}")
                transcripts = []
                
                for i, url in enumerate(youtube_urls, 1):
                    logger.info(f"�� Transcribing video {i}/{len(youtube_urls)}: {url}")
                    transcript = self.transcribe_youtube_video(url)
                    if transcript:
                        transcripts.append(f"=== VIDEO {i} TRANSCRIPT ===\n{transcript}\n")
                    else:
                        transcripts.append(f"=== VIDEO {i} TRANSCRIPT ===\n[Transcription failed]\n")
                
                yt_transcript = "\n".join(transcripts)
                logger.info(f"✅ YouTube transcription completed for page: {item['title']}")
            
            # Store page content with transcript
            self.cursor.execute("""
                INSERT INTO pages (id, module_item_id, title, body, front_page, yt_transcript, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    body = EXCLUDED.body,
                    front_page = EXCLUDED.front_page,
                    yt_transcript = EXCLUDED.yt_transcript,
                    updated_at = EXCLUDED.updated_at
            """, (
                page_content['page_id'],
                item['id'],
                page_content['title'],
                self.clean_html(page_content.get('body', '')),
                page_content.get('front_page', False),
                yt_transcript,
                page_content.get('created_at'),
                page_content.get('updated_at')
            ))
            
            logger.info(f"✅ Stored page content for item {item['id']}")
            
        except Exception as e:
            logger.error(f"❌ Error storing page content for item {item['id']}: {e}")
    
    
    def store_canvas_data_for_course(self, course_id: int) -> bool:
        """Fetch and store Canvas data for a single course"""
        try:
            logger.info(f"🚀 Starting data extraction for course {course_id}...")

            # Fetch modules
            url = f"{CANVAS_URL}/api/v1/courses/{course_id}/modules"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            modules = response.json()

            if not modules:
                logger.warning(f"⚠️ No modules found for course {course_id}")
                return False

            # Store modules with course mapping
            if not self.store_modules(modules, course_id):  # <-- pass course_id
                return False

            total_items = 0
            for module in modules:
                module_id = module['id']
                logger.info(f"📦 Processing module: {module['name']} (ID: {module_id})")

                items = self.fetch_module_items(module_id, course_id)  # <-- pass course_id
                if items:
                    if self.store_module_items(module_id, items, course_id):
                        total_items += len(items)
                    else:
                        logger.warning(f"⚠️ Failed to store items for module {module_id}")

            logger.info(f"✅ Course {course_id} done: {len(modules)} modules, {total_items} items")
            return True
        except Exception as e:
            logger.error(f"❌ Error processing course {course_id}: {e}")
            return False

def main():
    """Main function"""
    print("🎓 Canvas to PostgreSQL Data Storage with YouTube Transcription")
    print("=" * 70)
    
    # Check dependencies
    try:
        print("✅ Whisper is available")
    except ImportError:
        print("❌ Whisper not found. Install with: pip install openai-whisper")
        return
    
    try:
        subprocess.run(["yt-dlp", "--version"], check=True, capture_output=True)
        print("✅ yt-dlp is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ yt-dlp not found. Install with: pip install yt-dlp")
        return
    
    # Update database password
    # print("⚠️  Please update the DB_CONFIG password in the script before running!")
    # print("Current config:", DB_CONFIG)
    
    # Create data store instance
    store = CanvasDataStore(DB_CONFIG)
    
    # Connect to database
    if not store.connect_db():
        print("❌ Failed to connect to database")
        return
    
    try:
        # Store Canvas data
        all_courses = store.get_all_courses()
        for course_id in all_courses:
            success = store.store_canvas_data_for_course(course_id)
            if success:
                print("\n🎉 Data storage completed successfully!")
                print("🚀 Your Canvas data with YouTube transcripts is now in PostgreSQL!")
            else:
                print("\n💥 Data storage failed!")
            
    except KeyboardInterrupt:
        print("\n⏹️ Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        store.close_db()