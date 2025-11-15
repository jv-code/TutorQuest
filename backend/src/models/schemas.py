from pydantic import BaseModel
from typing import Optional, Literal, Dict, Any, List
from datetime import datetime

class SessionCreate(BaseModel):
    user_id: str
    session_id: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    created_at: datetime

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    video_url: Optional[str] = None

class MessageCreate(BaseModel):
    session_id: str
    content: str

class MessageResponse(BaseModel):
    message: Message
    question_id: Optional[str] = None

class QuestionResponse(BaseModel):
    question_id: str
    question: str
    topic: str
    difficulty: int

class AnswerValidate(BaseModel):
    session_id: str
    question_id: str
    answer: str

class AnswerValidationResponse(BaseModel):
    correct: bool
    attempts: int
    feedback: str
    offer_video: bool
    question: str
    topic: str

class VideoGenerateRequest(BaseModel):
    question_id: str
    session_id: str

class VideoStatusResponse(BaseModel):
    video_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    video_url: Optional[str] = None
    error: Optional[str] = None

# Webhook schemas for Clerk user events
class EmailAddress(BaseModel):
    id: str
    email_address: str
    verification: Optional[Dict[str, Any]] = None

class ClerkUserData(BaseModel):
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email_addresses: List[EmailAddress] = []
    primary_email_address_id: Optional[str] = None
    image_url: Optional[str] = None
    profile_image_url: Optional[str] = None
    created_at: int  # Unix timestamp in milliseconds
    updated_at: int  # Unix timestamp in milliseconds
    public_metadata: Optional[Dict[str, Any]] = None
    private_metadata: Optional[Dict[str, Any]] = None
    unsafe_metadata: Optional[Dict[str, Any]] = None

class ClerkWebhookPayload(BaseModel):
    data: ClerkUserData
    object: str
    type: str  # e.g., "user.created", "user.updated", "user.deleted"
    instance_id: Optional[str] = None
    timestamp: Optional[int] = None

class UserResponse(BaseModel):
    id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    image_url: Optional[str] = None
    subscription_tier: str = "free"
    subscription_status: str = "active"
    created_at: datetime
    updated_at: datetime
