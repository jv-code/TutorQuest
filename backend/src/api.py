from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uuid
from datetime import datetime
import sys
import traceback

# Use try/except for imports to support both local and Vercel environments
# Local: imports as src.api (needs src. prefix)
# Vercel: PYTHONPATH=backend/src (no src. prefix needed)
try:
    # Try Vercel-style imports first (no src. prefix)
    import models.schemas
    from models.schemas import (
        SessionCreate, SessionResponse, MessageCreate, MessageResponse,
        QuestionResponse, AnswerValidate, AnswerValidationResponse,
        VideoGenerateRequest, VideoStatusResponse, Message,
        ClerkWebhookPayload, UserResponse
    )
    from db.supabase import supabase
    from services.chat import chat_response
    from services.questions import get_next_question, validate_user_answer, generate_video_for_question
    from services.video import cleanup_old_videos
    from services.webhook import verify_webhook_signature, extract_primary_email
    from config import settings
except ModuleNotFoundError:
    # Fall back to local-style imports (with src. prefix)
    from src.models.schemas import (
        SessionCreate, SessionResponse, MessageCreate, MessageResponse,
        QuestionResponse, AnswerValidate, AnswerValidationResponse,
        VideoGenerateRequest, VideoStatusResponse, Message,
        ClerkWebhookPayload, UserResponse
    )
    from src.db.supabase import supabase
    from src.services.chat import chat_response
    from src.services.questions import get_next_question, validate_user_answer, generate_video_for_question
    from src.services.video import cleanup_old_videos
    from src.services.webhook import verify_webhook_signature, extract_primary_email
    from src.config import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health_check():
    """Health check endpoint to verify API is running"""
    return {
        "status": "healthy",
        "message": "API is running",
        "endpoints": {
            "sessions": "/sessions",
            "messages": "/messages",
            "questions": "/questions/next",
            "validate": "/questions/validate"
        }
    }

@app.post("/sessions", response_model=SessionResponse)
async def create_session(session_create: SessionCreate):
    try:
        session_id = session_create.session_id or str(uuid.uuid4())
        user_id = session_create.user_id
        created_at = datetime.utcnow()

        supabase.table("sessions").update({"is_active": False}).eq("user_id", user_id).execute()

        supabase.table("sessions").insert({
            "id": session_id,
            "user_id": user_id,
            "is_active": True,
            "created_at": created_at.isoformat()
        }).execute()

        return SessionResponse(session_id=session_id, user_id=user_id, created_at=created_at)
    except Exception as e:
        import sys
        import traceback
        print(f"ERROR in create_session: {e}", file=sys.stderr)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@app.post("/messages", response_model=MessageResponse)
async def send_message(message_create: MessageCreate):
    session_id = message_create.session_id
    user_content = message_create.content

    session = supabase.table("sessions").select("user_id").eq("id", session_id).single().execute()
    user_id = session.data["user_id"]

    result = supabase.table("messages").select("*").eq("session_id", session_id).order("created_at").execute()
    history = [{"role": msg["role"], "content": msg["content"]} for msg in result.data] if result.data else []

    history.append({"role": "user", "content": user_content})

    assistant_content = chat_response(history)

    supabase.table("messages").insert({
        "session_id": session_id,
        "user_id": user_id,
        "role": "user",
        "content": user_content,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    supabase.table("messages").insert({
        "session_id": session_id,
        "user_id": user_id,
        "role": "assistant",
        "content": assistant_content,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    return MessageResponse(
        message=Message(role="assistant", content=assistant_content),
        question_id=None
    )

@app.get("/messages/{session_id}")
async def get_messages(session_id: str):
    result = supabase.table("messages").select("*").eq("session_id", session_id).order("created_at").execute()
    return {"messages": result.data or []}

@app.get("/questions/next", response_model=QuestionResponse)
async def next_question(session_id: str, difficulty: int = None):
    question = get_next_question(session_id, difficulty)
    return QuestionResponse(**question)

@app.post("/questions/validate", response_model=AnswerValidationResponse)
async def validate_answer(answer_validate: AnswerValidate):
    result = validate_user_answer(
        answer_validate.session_id,
        answer_validate.question_id,
        answer_validate.answer
    )
    return AnswerValidationResponse(**result)

@app.post("/videos/generate")
async def generate_video_endpoint(video_request: VideoGenerateRequest):
    video_result = generate_video_for_question(video_request.session_id, video_request.question_id)
    return video_result

@app.post("/videos/cleanup")
async def cleanup_videos():
    result = cleanup_old_videos()
    return result

@app.post("/webhooks/clerk")
async def clerk_webhook(request: Request):
    """
    Webhook endpoint for Clerk user events (user.created, user.updated, user.deleted).
    Verifies Svix signature and processes user data into Supabase.
    """
    try:
        # Verify webhook signature and get payload
        if not settings.clerk_webhook_secret:
            print("WARNING: CLERK_WEBHOOK_SECRET not set, skipping signature verification", file=sys.stderr)
            payload_dict = await request.json()
        else:
            payload_dict = await verify_webhook_signature(request, settings.clerk_webhook_secret)

        # Parse payload using Pydantic model
        payload = ClerkWebhookPayload(**payload_dict)

        # Extract user data
        user_data = payload.data
        event_type = payload.type

        print(f"Received webhook event: {event_type} for user {user_data.id}", file=sys.stderr)

        # Extract primary email
        primary_email = extract_primary_email(payload_dict.get("data", {}))

        # Handle different event types
        if event_type == "user.created":
            # Insert new user into database
            user_record = {
                "id": user_data.id,
                "email": primary_email,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "image_url": user_data.profile_image_url or user_data.image_url,
                "subscription_tier": "free",  # Default subscription tier
                "subscription_status": "active",  # Default status
                "metadata": {
                    "public_metadata": user_data.public_metadata,
                    "created_at_ms": user_data.created_at
                },
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            result = supabase.table("users").insert(user_record).execute()
            print(f"User created successfully: {user_data.id}", file=sys.stderr)

            return {
                "status": "success",
                "event": event_type,
                "user_id": user_data.id,
                "email": primary_email
            }

        elif event_type == "user.updated":
            # Update existing user
            user_updates = {
                "email": primary_email,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "image_url": user_data.profile_image_url or user_data.image_url,
                "metadata": {
                    "public_metadata": user_data.public_metadata,
                    "updated_at_ms": user_data.updated_at
                },
                "updated_at": datetime.utcnow().isoformat()
            }

            result = supabase.table("users").update(user_updates).eq("id", user_data.id).execute()
            print(f"User updated successfully: {user_data.id}", file=sys.stderr)

            return {
                "status": "success",
                "event": event_type,
                "user_id": user_data.id,
                "email": primary_email
            }

        elif event_type == "user.deleted":
            # Soft delete or mark user as inactive (or hard delete if preferred)
            # For now, we'll just mark as inactive
            result = supabase.table("users").update({
                "subscription_status": "deleted",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", user_data.id).execute()
            print(f"User marked as deleted: {user_data.id}", file=sys.stderr)

            return {
                "status": "success",
                "event": event_type,
                "user_id": user_data.id
            }

        else:
            print(f"Unhandled event type: {event_type}", file=sys.stderr)
            return {
                "status": "ignored",
                "event": event_type,
                "message": f"Event type {event_type} not handled"
            }

    except Exception as e:
        print(f"ERROR in clerk_webhook: {e}", file=sys.stderr)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user information by Clerk user ID"""
    try:
        result = supabase.table("users").select("*").eq("id", user_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")

        return UserResponse(**result.data[0])
    except Exception as e:
        print(f"ERROR in get_user: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Failed to fetch user: {str(e)}")
