from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, List, Dict, Any

Base = declarative_base()

class Course(Base):
    """Course information from Canvas"""
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True)
    canvas_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan")
    pages = relationship("Page", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")

class Module(Base):
    """Module information from Canvas"""
    __tablename__ = "modules"
    
    id = Column(Integer, primary_key=True)
    canvas_id = Column(String(50), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    position = Column(Integer, default=0)
    published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    course = relationship("Course", back_populates="modules")
    items = relationship("ModuleItem", back_populates="module", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_module_course_position', 'course_id', 'position'),
        Index('idx_module_canvas_id', 'canvas_id'),
    )

class ModuleItem(Base):
    """Individual items within modules (pages, assignments, discussions, etc.)"""
    __tablename__ = "module_items"
    
    id = Column(Integer, primary_key=True)
    canvas_id = Column(String(50), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # page, assignment, discussion, quiz, etc.
    content_id = Column(String(50))  # ID of the actual content item
    position = Column(Integer, default=0)
    published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    module = relationship("Module", back_populates="items")
    knowledge_content = relationship("KnowledgeContent", back_populates="module_item", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_module_item_module_position', 'module_id', 'position'),
        Index('idx_module_item_type', 'type'),
        Index('idx_module_item_canvas_id', 'canvas_id'),
    )

class Page(Base):
    """Page content from Canvas"""
    __tablename__ = "pages"
    
    id = Column(Integer, primary_key=True)
    canvas_id = Column(String(50), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    body = Column(Text)
    published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    course = relationship("Course", back_populates="pages")
    knowledge_content = relationship("KnowledgeContent", back_populates="page", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_page_course_slug', 'course_id', 'slug'),
        Index('idx_page_canvas_id', 'canvas_id'),
    )

class Assignment(Base):
    """Assignment information from Canvas"""
    __tablename__ = "assignments"
    
    id = Column(Integer, primary_key=True)
    canvas_id = Column(String(50), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    due_date = Column(DateTime)
    published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    course = relationship("Course", back_populates="assignments")
    knowledge_content = relationship("KnowledgeContent", back_populates="assignment", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_assignment_course', 'course_id'),
        Index('idx_assignment_canvas_id', 'canvas_id'),
    )

class KnowledgeContent(Base):
    """Processed and cleaned knowledge base content"""
    __tablename__ = "knowledge_content"
    
    id = Column(Integer, primary_key=True)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256 hash of content
    content_type = Column(String(50), nullable=False)  # course, module, page, assignment, module_item
    
    # Foreign keys to different content types
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=True)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=True)
    module_item_id = Column(Integer, ForeignKey("module_items.id"), nullable=True)
    
    # Content fields
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    clean_content = Column(Text, nullable=False)  # HTML-cleaned content
    content_summary = Column(Text)  # AI-generated summary
    keywords = Column(Text)  # JSON array of extracted keywords
    relevance_score = Column(Float, default=1.0)
    
    # Metadata
    language = Column(String(10), default="en")
    difficulty_level = Column(String(20), default="medium")  # easy, medium, hard
    content_length = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    
    # Processing info
    processed_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    access_count = Column(Integer, default=0)
    
    # Relationships
    course = relationship("Course")
    module = relationship("Module")
    page = relationship("Page")
    assignment = relationship("Assignment")
    module_item = relationship("ModuleItem", back_populates="knowledge_content")
    
    # Indexes
    __table_args__ = (
        Index('idx_knowledge_content_type', 'content_type'),
        Index('idx_knowledge_content_language', 'language'),
        Index('idx_knowledge_content_difficulty', 'difficulty_level'),
        Index('idx_knowledge_content_relevance', 'relevance_score'),
        Index('idx_knowledge_content_processed', 'processed_at'),
        Index('idx_knowledge_content_accessed', 'last_accessed'),
    )

class ContentVector(Base):
    """Vector embeddings for semantic search"""
    __tablename__ = "content_vectors"
    
    id = Column(Integer, primary_key=True)
    knowledge_content_id = Column(Integer, ForeignKey("knowledge_content.id"), nullable=False)
    embedding_model = Column(String(100), nullable=False)  # e.g., "text-embedding-ada-002"
    vector_data = Column(Text, nullable=False)  # JSON array of vector values
    vector_dimension = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    knowledge_content = relationship("KnowledgeContent")
    
    # Indexes
    __table_args__ = (
        Index('idx_content_vector_model', 'embedding_model'),
        Index('idx_content_vector_content', 'knowledge_content_id'),
    )

class ContentUpdateLog(Base):
    """Log of content updates and sync operations"""
    __tablename__ = "content_update_log"
    
    id = Column(Integer, primary_key=True)
    operation = Column(String(50), nullable=False)  # create, update, delete, sync
    content_type = Column(String(50), nullable=False)
    content_id = Column(Integer, nullable=False)
    canvas_id = Column(String(50), nullable=False)
    status = Column(String(50), default="pending")  # pending, success, failed
    error_message = Column(Text)
    processed_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_update_log_operation', 'operation'),
        Index('idx_update_log_status', 'status'),
        Index('idx_update_log_processed', 'processed_at'),
    ) 