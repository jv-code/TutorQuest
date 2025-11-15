import uuid
from datetime import datetime
try:
    import services.chat
    from services.chat import generate_next_question, validate_answer as openai_validate, generate_hint
    from services.video import generate_video
    from db.supabase import supabase
except ModuleNotFoundError:
    from src.services.chat import generate_next_question, validate_answer as openai_validate, generate_hint
    from src.services.video import generate_video
    from src.db.supabase import supabase

def get_next_question(session_id: str, difficulty: int = None) -> dict:
    session = supabase.table("sessions").select("user_id").eq("id", session_id).single().execute()
    user_id = session.data["user_id"]

    all_questions = supabase.table("questions").select("*").eq("session_id", session_id).execute()

    if difficulty is None:
        question_count = len(all_questions.data) if all_questions.data else 0
        difficulty = min(1 + question_count // 3, 10)
    else:
        difficulty = max(1, min(10, difficulty))

    topic = "Long Division"

    previous_questions = [q["question"] for q in all_questions.data] if all_questions.data else []

    question_data = generate_next_question(topic, difficulty, previous_questions)

    question_id = str(uuid.uuid4())

    supabase.table("questions").insert({
        "id": question_id,
        "session_id": session_id,
        "user_id": user_id,
        "question": question_data["question"],
        "topic": question_data.get("topic", topic),
        "difficulty": difficulty,
        "attempts": 0,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    return {
        "question_id": question_id,
        "question": question_data["question"],
        "topic": question_data.get("topic", topic),
        "difficulty": difficulty
    }

def validate_user_answer(session_id: str, question_id: str, answer: str) -> dict:
    result = supabase.table("questions").select("*").eq("id", question_id).single().execute()
    question_data = result.data

    validation = openai_validate(question_data["question"], answer)

    new_attempts = question_data["attempts"] + 1

    supabase.table("questions").update({
        "attempts": new_attempts
    }).eq("id", question_id).execute()

    if validation["correct"]:
        feedback = validation["feedback"]
    elif new_attempts == 1:
        feedback = "Incorrect. Please try again."
    elif new_attempts == 2:
        hint = generate_hint(question_data["question"], answer)
        feedback = f"Not quite right. Here's a hint: {hint}"
    else:
        feedback = f"That's not correct. {validation['feedback']}"

    return {
        "correct": validation["correct"],
        "attempts": new_attempts,
        "feedback": feedback,
        "offer_video": not validation["correct"] and new_attempts >= 3,
        "question": question_data["question"],
        "topic": question_data["topic"]
    }

def generate_video_for_question(session_id: str, question_id: str) -> dict:
    result = supabase.table("questions").select("*").eq("id", question_id).single().execute()
    question_data = result.data

    video_result = generate_video(question_data["question"])

    return video_result
