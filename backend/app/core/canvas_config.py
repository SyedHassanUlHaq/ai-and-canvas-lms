"""
Canvas LMS Configuration and Settings
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv

load_dotenv()


class LanguageConfig(BaseModel):
    """Language-specific configuration"""
    code: str
    name: str
    native_name: str
    flag: str
    rtl: bool = False


class CanvasSettings(BaseModel):
    """Canvas LMS configuration settings"""
    
    # Canvas Instance Configuration
    canvas_url: str = Field(
        default=os.getenv("CANVAS_URL"),
        description="Canvas instance URL"
    )
    canvas_api_token: str = Field(
        default=os.getenv("CANVAS_API_TOKEN"),
        description="Canvas API access token"
    )
    
    # LTI Configuration
    lti_consumer_key: str = Field(
        default=os.getenv("LTI_CONSUMER_KEY"),
        description="LTI consumer key for authentication"
    )
    lti_shared_secret: str = Field(
        default=os.getenv("LTI_SHARED_SECRET"),
        description="LTI shared secret for authentication"
    )
    lti_version: str = Field(
        default="1.3",
        description="LTI version to use"
    )
    
    # Course Configuration
    demo_course_id: str = Field(
        default="",
        description="Canvas course ID for the demo course"
    )
    demo_course_name: str = Field(
        default="[DEMO] Introduction to Design Thinking Demo",
        description="Name of the demo course"
    )
    
    # Widget Configuration
    widget_title: str = Field(
        default="AI Tutor",
        description="Title for the chatbot widget"
    )
    widget_description: str = Field(
        default="Get help with your coursework from our AI tutor",
        description="Description for the chatbot widget"
    )
    
    # Language Settings - Bahasa Indonesia as default
    default_language: str = Field(
        default="id",  # Changed from "en" to "id" for Bahasa Indonesia
        description="Default language for the AI tutor (id=Indonesian, en=English)"
    )
    
    # Supported languages with full configuration
    supported_languages: List[LanguageConfig] = Field(
        default=[
            LanguageConfig(
                code="id",
                name="Indonesian",
                native_name="Bahasa Indonesia",
                flag="🇮🇩",
                rtl=False
            ),
            LanguageConfig(
                code="en",
                name="English",
                native_name="English",
                flag="🇺🇸",
                rtl=False
            )
        ],
        description="Supported languages with full configuration"
    )
    
    # Language detection settings
    auto_detect_language: bool = Field(
        default=True,
        description="Automatically detect user's language preference"
    )
    
    # Language-specific content mappings
    language_content: Dict[str, Dict[str, str]] = Field(
        default={
            "id": {
                "title": "AI Tutor",
                "welcome": "Halo! Saya adalah AI Tutor yang siap membantu Anda dengan pembelajaran. Silakan ajukan pertanyaan tentang modul yang sedang Anda pelajari.",
                "placeholder": "Ketik pertanyaan Anda di sini...",
                "send": "Kirim",
                "loading": "AI Tutor sedang memproses pertanyaan Anda...",
                "typing": "AI Tutor sedang mengetik",
                "error": "Maaf, terjadi kesalahan. Silakan coba lagi.",
                "welcome_with_context": "Halo! Saya adalah AI Tutor untuk modul ini. Silakan ajukan pertanyaan tentang konten yang sedang Anda pelajari.",
                "no_context": "Halo! Saya adalah AI Tutor. Silakan ajukan pertanyaan umum tentang pembelajaran.",
                "language_switch": "Beralih ke Bahasa Inggris",
                "course_context": "Kursus: {course_name}",
                "module_context": "Modul: {module_name}",
                "page_context": "Halaman: {page_name}",
                "memory_cleared": "Memori percakapan telah dibersihkan",
                "memory_error": "Gagal membersihkan memori",
                "history_summary": "Ringkasan percakapan",
                "topics_discussed": "Topik yang dibahas",
                "total_messages": "Total pesan"
            },
            "en": {
                "title": "AI Tutor",
                "welcome": "Hello! I am an AI Tutor ready to help you with your learning. Please ask questions about the module you are currently studying.",
                "placeholder": "Type your question here...",
                "send": "Send",
                "loading": "AI Tutor is processing your question...",
                "typing": "AI Tutor is typing",
                "error": "Sorry, an error occurred. Please try again.",
                "welcome_with_context": "Hello! I am an AI Tutor for this module. Please ask questions about the content you are currently studying.",
                "no_context": "Hello! I am an AI Tutor. Please ask general questions about learning.",
                "language_switch": "Switch to Bahasa Indonesia",
                "course_context": "Course: {course_name}",
                "module_context": "Module: {module_name}",
                "page_context": "Page: {page_name}",
                "memory_cleared": "Conversation memory has been cleared",
                "memory_error": "Failed to clear memory",
                "history_summary": "Conversation summary",
                "topics_discussed": "Topics discussed",
                "total_messages": "Total messages"
            }
        },
        description="Language-specific content for the UI"
    )
    
    # AI Tutor Behavior
    socratic_questioning: bool = Field(
        default=True,
        description="Enable Socratic questioning approach"
    )
    formative_assessment: bool = Field(
        default=True,
        description="Enable formative assessment features"
    )
    module_context_only: bool = Field(
        default=True,
        description="Restrict answers to current module content only (Canvas content only, no vector database)"
    )
    adaptive_difficulty: bool = Field(
        default=True,
        description="Enable adaptive difficulty based on quiz results"
    )
    academic_integrity: bool = Field(
        default=True,
        description="Enable academic integrity features"
    )
    
    # Language detection methods
    def get_language_by_code(self, code: str) -> Optional[LanguageConfig]:
        """Get language configuration by language code"""
        for lang in self.supported_languages:
            if lang.code == code:
                return lang
        return None
    
    def get_default_language_config(self) -> LanguageConfig:
        """Get the default language configuration"""
        return self.get_language_by_code(self.default_language) or self.supported_languages[0]
    
    def get_language_content(self, language_code: str, key: str, **kwargs) -> str:
        """Get language-specific content with optional formatting"""
        if language_code not in self.language_content:
            language_code = self.default_language
        
        content = self.language_content[language_code].get(key, "")
        
        # Apply formatting if kwargs are provided
        if kwargs:
            try:
                content = content.format(**kwargs)
            except (KeyError, ValueError):
                pass
        
        return content
    
    def detect_user_language(self, accept_language: str = None, user_preference: str = None) -> str:
        """Detect user's preferred language from various sources"""
        # Priority: 1. User preference, 2. Accept-Language header, 3. Default
        if user_preference and self.get_language_by_code(user_preference):
            return user_preference
        
        if accept_language and self.auto_detect_language:
            # Parse Accept-Language header (e.g., "en-US,en;q=0.9,id;q=0.8")
            languages = accept_language.split(',')
            for lang in languages:
                # Extract language code (e.g., "en-US" -> "en")
                lang_code = lang.split(';')[0].split('-')[0].strip()
                if self.get_language_by_code(lang_code):
                    return lang_code
        
        return self.default_language


# Create settings instance
canvas_settings = CanvasSettings()

# Configuration is now hardcoded above - no need for environment variable overrides 