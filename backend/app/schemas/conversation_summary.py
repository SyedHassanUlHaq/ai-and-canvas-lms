from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

class ConversationMemoryBase(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    user_name: str = Field(..., min_lenth=1, max_length=200)
    course_id: str = Field(..., min_length=1, max_length=50)
    module_item_id: Optional[str] = Field(None, max_length=50)
    message: str = Field(..., min_length=1)
    message_from: str = Field(default='user', pattern='^(user|assistant)$')
    session_id: str = Field(..., min_length=1, max_length=100)

class ConversationMemoryCreate(ConversationMemoryBase):
    pass

class ConversationMemoryUpdate(BaseModel):
    message: Optional[str] = Field(None, min_length=1)
    message_from: Optional[str] = Field(None, pattern='^(user|assistant)$')

class ConversationMemoryResponse(ConversationMemoryBase):
    id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True
    
    @property
    def context_used_dict(self) -> Optional[Dict[str, Any]]:
        """Helper property to get context_used as dict"""
        if self.context_used:
            return json.loads(self.context_used)
        return None

class ConversationMemoryResponseList(BaseModel):
    items: List[ConversationMemoryResponse]
    total_count: int