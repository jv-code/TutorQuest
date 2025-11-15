# Implementation Guide: User-Scoped Learning Architecture

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React 19)                       │
│  ├─ useUserProgress → level, streak, weak topics           │
│  ├─ useQuestions → current Q, validation, next Q           │
│  ├─ useChat → messages, context injection                  │
│  ├─ useVideos → generation, polling, playback              │
│  └─ useTTS → Web Speech API, autoplay                      │
└─────────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                          │
│  ├─ UserProgressService → level calc, mastery tracking     │
│  ├─ TopicService → curriculum DAG, recommendations         │
│  ├─ QuestionService → smart selection, deduplication       │
│  ├─ ChatService → context building, Claude integration     │
│  └─ VideoService → dual generation (code + explanation)    │
└─────────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────────┐
│              DATABASE (Supabase PostgreSQL)                  │
│  ├─ users, user_progress                                   │
│  ├─ topics, user_topic_progress                            │
│  ├─ questions, user_question_attempts                      │
│  ├─ sessions, messages                                     │
│  └─ videos (with explanation_data JSONB)                   │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

### 1. New Tables

```sql
CREATE TABLE user_progress (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    current_level INTEGER DEFAULT 1 CHECK (current_level BETWEEN 1 AND 10),
    total_questions_attempted INTEGER DEFAULT 0,
    total_questions_correct INTEGER DEFAULT 0,
    current_streak INTEGER DEFAULT 0,
    best_streak INTEGER DEFAULT 0,
    last_practice_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE topics (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    level_range INTEGER[] NOT NULL,
    prerequisite_topic_ids TEXT[],
    concept_tags TEXT[],
    difficulty_weight DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE user_topic_progress (
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    topic_id TEXT REFERENCES topics(id) ON DELETE CASCADE,
    questions_attempted INTEGER DEFAULT 0,
    questions_correct INTEGER DEFAULT 0,
    mastery_percentage DECIMAL(5,2) DEFAULT 0.0,
    first_attempted TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_attempted TIMESTAMP WITH TIME ZONE,
    needs_review BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (user_id, topic_id)
);

CREATE TABLE user_question_attempts (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    question_id TEXT REFERENCES questions(id) ON DELETE CASCADE,
    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    attempts_made INTEGER DEFAULT 0,
    is_correct BOOLEAN,
    user_answer TEXT,
    time_spent_seconds INTEGER,
    video_requested BOOLEAN DEFAULT FALSE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, question_id)
);
```

### 2. Enhanced Existing Tables

```sql
ALTER TABLE questions
    ADD COLUMN dividend INTEGER,
    ADD COLUMN divisor INTEGER,
    ADD COLUMN correct_answer INTEGER,
    ADD COLUMN remainder INTEGER DEFAULT 0,
    ADD COLUMN topic_id TEXT REFERENCES topics(id),
    ADD COLUMN question_signature TEXT,
    ADD COLUMN times_served INTEGER DEFAULT 0;

ALTER TABLE videos
    ADD COLUMN explanation_data JSONB;

ALTER TABLE sessions
    ADD COLUMN session_type TEXT DEFAULT 'practice',
    ADD COLUMN ended_at TIMESTAMP WITH TIME ZONE;
```

### 3. Indexes

```sql
CREATE INDEX idx_user_progress_level ON user_progress(current_level);
CREATE INDEX idx_user_topic_progress_user ON user_topic_progress(user_id);
CREATE INDEX idx_user_topic_progress_mastery ON user_topic_progress(user_id, mastery_percentage);
CREATE INDEX idx_user_question_attempts_user_question ON user_question_attempts(user_id, question_id);
CREATE INDEX idx_questions_level_topic ON questions(difficulty, topic_id);
CREATE INDEX idx_questions_signature ON questions(question_signature);
CREATE INDEX idx_videos_user_recent ON videos(user_id, created_at DESC);
CREATE INDEX idx_sessions_user_active ON sessions(user_id, is_active);
CREATE INDEX idx_messages_session ON messages(session_id, created_at DESC);
```

### 4. Seed Data - Topics

```sql
INSERT INTO topics (id, name, description, level_range, prerequisite_topic_ids, concept_tags, difficulty_weight) VALUES
('basic-division-1digit', 'Basic Division (1-digit divisor)', 'Simple division with single-digit divisors and no remainders', ARRAY[1, 2], ARRAY[]::text[], ARRAY['division', 'quotient', 'equal-groups'], 1.0),
('division-remainders', 'Division with Remainders', 'Division problems that don''t divide evenly', ARRAY[3, 4], ARRAY['basic-division-1digit'], ARRAY['division', 'remainder', 'quotient'], 1.2),
('multi-digit-division', 'Multi-digit Division', 'Division with 3-digit dividends and 1-digit divisors', ARRAY[5, 6], ARRAY['division-remainders'], ARRAY['long-division', 'place-value', 'multi-step'], 1.5),
('two-digit-divisors', 'Two-digit Divisors', 'Division with two-digit divisors', ARRAY[7, 8], ARRAY['multi-digit-division'], ARRAY['long-division', 'estimation', 'two-digit-divisor'], 1.8),
('complex-division', 'Complex Division', 'Advanced division with 4-digit dividends and 2-digit divisors', ARRAY[9, 10], ARRAY['two-digit-divisors'], ARRAY['long-division', 'complex', 'multi-step'], 2.0);
```

## Backend Services

### File Structure

```
backend/src/
├── models/
│   ├── schemas.py (enhanced)
│   └── database.py (new - SQLAlchemy models if using ORM)
├── services/
│   ├── user_progress.py (new)
│   ├── topics.py (new)
│   ├── questions.py (enhanced)
│   ├── chat.py (enhanced)
│   └── video.py (enhanced)
├── db/
│   └── supabase.py (existing)
└── api.py (enhanced)
```

### 1. UserProgressService

**File:** `backend/src/services/user_progress.py`

```python
from typing import Optional
from datetime import datetime

class UserProgressService:
    def __init__(self, db_client):
        self.db = db_client

    def get_progress(self, user_id: str):
        result = self.db.table('user_progress').select('*').eq('user_id', user_id).execute()
        if not result.data:
            return self.create_progress(user_id)
        return result.data[0]

    def create_progress(self, user_id: str):
        data = {
            'user_id': user_id,
            'current_level': 1,
            'total_questions_attempted': 0,
            'total_questions_correct': 0,
            'current_streak': 0,
            'best_streak': 0,
            'last_practice_date': datetime.now().isoformat()
        }
        result = self.db.table('user_progress').insert(data).execute()
        return result.data[0]

    def update_after_question(self, user_id: str, is_correct: bool):
        progress = self.get_progress(user_id)

        new_streak = (progress['current_streak'] + 1) if is_correct else 0
        new_best = max(new_streak, progress['best_streak'])

        updates = {
            'total_questions_attempted': progress['total_questions_attempted'] + 1,
            'total_questions_correct': progress['total_questions_correct'] + (1 if is_correct else 0),
            'current_streak': new_streak,
            'best_streak': new_best,
            'last_practice_date': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        self.db.table('user_progress').update(updates).eq('user_id', user_id).execute()

        new_level = self.calculate_next_level(user_id)
        if new_level != progress['current_level']:
            self.db.table('user_progress').update({'current_level': new_level}).eq('user_id', user_id).execute()

        return new_level

    def calculate_next_level(self, user_id: str):
        progress = self.get_progress(user_id)
        current_level = progress['current_level']

        topics_result = self.db.table('topics').select('id').contains('level_range', [current_level]).execute()
        topic_ids = [t['id'] for t in topics_result.data]

        if not topic_ids:
            return current_level

        mastery_result = self.db.table('user_topic_progress').select('mastery_percentage').eq('user_id', user_id).in_('topic_id', topic_ids).execute()

        if not mastery_result.data:
            return current_level

        avg_mastery = sum(m['mastery_percentage'] for m in mastery_result.data) / len(mastery_result.data)

        if avg_mastery >= 80 and progress['current_streak'] >= 3:
            return min(current_level + 1, 10)

        if avg_mastery < 40 and progress['total_questions_attempted'] >= 5:
            return max(current_level - 1, 1)

        return current_level

    def get_weak_topics(self, user_id: str, current_level: Optional[int] = None):
        query = self.db.table('user_topic_progress').select('*, topics(*)').eq('user_id', user_id).lt('mastery_percentage', 60)

        if current_level:
            topics_result = self.db.table('topics').select('id').contains('level_range', [current_level]).execute()
            topic_ids = [t['id'] for t in topics_result.data]
            if topic_ids:
                query = query.in_('topic_id', topic_ids)

        result = query.execute()
        return result.data
```

### 2. TopicService

**File:** `backend/src/services/topics.py`

```python
class TopicService:
    def __init__(self, db_client):
        self.db = db_client

    def get_all_topics(self):
        result = self.db.table('topics').select('*').execute()
        return result.data

    def get_topic(self, topic_id: str):
        result = self.db.table('topics').select('*').eq('id', topic_id).execute()
        return result.data[0] if result.data else None

    def get_user_topic_progress(self, user_id: str):
        result = self.db.table('user_topic_progress').select('*, topics(*)').eq('user_id', user_id).execute()
        return result.data

    def update_topic_mastery(self, user_id: str, topic_id: str, is_correct: bool):
        result = self.db.table('user_topic_progress').select('*').eq('user_id', user_id).eq('topic_id', topic_id).execute()

        if not result.data:
            data = {
                'user_id': user_id,
                'topic_id': topic_id,
                'questions_attempted': 1,
                'questions_correct': 1 if is_correct else 0,
                'mastery_percentage': 100.0 if is_correct else 0.0,
                'last_attempted': datetime.now().isoformat()
            }
            self.db.table('user_topic_progress').insert(data).execute()
        else:
            progress = result.data[0]
            new_attempted = progress['questions_attempted'] + 1
            new_correct = progress['questions_correct'] + (1 if is_correct else 0)
            new_mastery = (new_correct / new_attempted) * 100

            updates = {
                'questions_attempted': new_attempted,
                'questions_correct': new_correct,
                'mastery_percentage': round(new_mastery, 2),
                'last_attempted': datetime.now().isoformat(),
                'needs_review': new_mastery < 60
            }

            self.db.table('user_topic_progress').update(updates).eq('user_id', user_id).eq('topic_id', topic_id).execute()

    def get_recommended_topic(self, user_id: str, current_level: int):
        weak_topics = self.db.table('user_topic_progress').select('topic_id').eq('user_id', user_id).eq('needs_review', True).execute()

        if weak_topics.data:
            return weak_topics.data[0]['topic_id']

        available_topics = self.db.table('topics').select('*').contains('level_range', [current_level]).execute()

        attempted_topics = self.db.table('user_topic_progress').select('topic_id').eq('user_id', user_id).execute()
        attempted_ids = {t['topic_id'] for t in attempted_topics.data}

        new_topics = [t for t in available_topics.data if t['id'] not in attempted_ids]

        if new_topics:
            return new_topics[0]['id']

        return available_topics.data[0]['id'] if available_topics.data else None
```

### 3. QuestionService (Enhanced)

**File:** `backend/src/services/questions.py`

```python
import random
from typing import Optional

class QuestionService:
    def __init__(self, db_client, user_progress_service, topic_service):
        self.db = db_client
        self.user_progress = user_progress_service
        self.topics = topic_service

    def generate_next_question(self, user_id: str):
        progress = self.user_progress.get_progress(user_id)
        current_level = progress['current_level']

        weak_topics = self.user_progress.get_weak_topics(user_id, current_level)
        target_topic_ids = [t['topic_id'] for t in weak_topics]

        if not target_topic_ids:
            recommended_topic = self.topics.get_recommended_topic(user_id, current_level)
            target_topic_ids = [recommended_topic] if recommended_topic else []

        attempted_questions = self.db.table('user_question_attempts').select('question_id').eq('user_id', user_id).execute()
        attempted_ids = [q['question_id'] for q in attempted_questions.data]

        query = self.db.table('questions').select('*').eq('difficulty', current_level)

        if target_topic_ids:
            query = query.in_('topic_id', target_topic_ids)

        if attempted_ids:
            query = query.not_.in_('id', attempted_ids)

        available_questions = query.execute()

        if not available_questions.data:
            topic_id = target_topic_ids[0] if target_topic_ids else self.topics.get_recommended_topic(user_id, current_level)
            return self.generate_unique_question(user_id, topic_id, current_level)

        return random.choice(available_questions.data)

    def generate_unique_question(self, user_id: str, topic_id: str, level: int):
        dividend, divisor = self.generate_division_params(level)
        signature = f"{dividend}÷{divisor}"

        existing = self.db.table('user_question_attempts').select('question_id, questions!inner(question_signature)').eq('user_id', user_id).eq('questions.question_signature', signature).execute()

        max_attempts = 50
        attempts = 0
        while existing.data and attempts < max_attempts:
            dividend, divisor = self.generate_division_params(level)
            signature = f"{dividend}÷{divisor}"
            existing = self.db.table('user_question_attempts').select('question_id, questions!inner(question_signature)').eq('user_id', user_id).eq('questions.question_signature', signature).execute()
            attempts += 1

        answer = dividend // divisor
        remainder = dividend % divisor

        question_data = {
            'dividend': dividend,
            'divisor': divisor,
            'correct_answer': answer,
            'remainder': remainder,
            'question': f"What is {dividend} ÷ {divisor}?",
            'topic_id': topic_id,
            'difficulty': level,
            'question_signature': signature,
            'user_id': user_id,
            'attempts': 0
        }

        result = self.db.table('questions').insert(question_data).execute()
        return result.data[0]

    def generate_division_params(self, level: int):
        if level <= 2:
            divisor = random.randint(2, 9)
            quotient = random.randint(2, 9)
            dividend = divisor * quotient
        elif level <= 4:
            divisor = random.randint(2, 9)
            quotient = random.randint(2, 12)
            dividend = divisor * quotient + random.randint(0, divisor - 1)
        elif level <= 6:
            divisor = random.randint(6, 12)
            quotient = random.randint(10, 99)
            dividend = divisor * quotient + random.randint(0, divisor - 1)
        elif level <= 8:
            divisor = random.randint(11, 25)
            quotient = random.randint(5, 20)
            dividend = divisor * quotient + random.randint(0, divisor - 1)
        else:
            divisor = random.randint(20, 50)
            quotient = random.randint(10, 99)
            dividend = divisor * quotient + random.randint(0, divisor - 1)

        return dividend, divisor

    def validate_answer(self, user_id: str, question_id: str, user_answer: str, session_id: str):
        question = self.db.table('questions').select('*').eq('id', question_id).execute().data[0]

        is_correct = str(question['correct_answer']) == str(user_answer).strip()

        attempt_result = self.db.table('user_question_attempts').select('*').eq('user_id', user_id).eq('question_id', question_id).execute()

        if not attempt_result.data:
            attempt_data = {
                'user_id': user_id,
                'question_id': question_id,
                'session_id': session_id,
                'attempts_made': 1,
                'is_correct': is_correct,
                'user_answer': user_answer,
                'started_at': datetime.now().isoformat()
            }
            self.db.table('user_question_attempts').insert(attempt_data).execute()
            attempts = 1
        else:
            attempt = attempt_result.data[0]
            attempts = attempt['attempts_made'] + 1

            updates = {
                'attempts_made': attempts,
                'is_correct': is_correct,
                'user_answer': user_answer
            }

            if is_correct:
                updates['completed_at'] = datetime.now().isoformat()

            self.db.table('user_question_attempts').update(updates).eq('user_id', user_id).eq('question_id', question_id).execute()

        self.db.table('questions').update({'attempts': question.get('attempts', 0) + 1}).eq('id', question_id).execute()

        if is_correct:
            self.topics.update_topic_mastery(user_id, question['topic_id'], True)
            new_level = self.user_progress.update_after_question(user_id, True)
        else:
            if attempts >= 3:
                self.topics.update_topic_mastery(user_id, question['topic_id'], False)
            new_level = self.user_progress.get_progress(user_id)['current_level']

        return {
            'is_correct': is_correct,
            'attempts': attempts,
            'offer_video': attempts >= 3 and not is_correct,
            'new_level': new_level,
            'correct_answer': question['correct_answer'] if not is_correct else None
        }
```

### 4. ChatService (Enhanced)

**File:** `backend/src/services/chat.py`

```python
import json
from anthropic import Anthropic

class ChatService:
    def __init__(self, db_client, anthropic_client):
        self.db = db_client
        self.claude = anthropic_client

    def send_message(self, user_id: str, session_id: str, message: str):
        context = self.build_chat_context(user_id, session_id)

        system_prompt = self.build_system_prompt(context)

        messages_result = self.db.table('messages').select('role, content').eq('session_id', session_id).order('created_at').execute()

        conversation_history = [{"role": m['role'], "content": m['content']} for m in messages_result.data[-10:]]
        conversation_history.append({"role": "user", "content": message})

        response = self.claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_prompt,
            messages=conversation_history
        )

        assistant_message = response.content[0].text

        self.db.table('messages').insert({'session_id': session_id, 'user_id': user_id, 'role': 'user', 'content': message}).execute()
        self.db.table('messages').insert({'session_id': session_id, 'user_id': user_id, 'role': 'assistant', 'content': assistant_message}).execute()

        return assistant_message

    def build_chat_context(self, user_id: str, session_id: str):
        session = self.db.table('sessions').select('*').eq('id', session_id).execute().data[0]

        current_question = self.db.table('questions').select('*').eq('session_id', session_id).order('created_at', desc=True).limit(1).execute()

        recent_videos = self.db.table('videos').select('*, questions(*)').eq('user_id', user_id).eq('status', 'ready').order('created_at', desc=True).limit(3).execute()

        weak_topics = self.db.table('user_topic_progress').select('*, topics(*)').eq('user_id', user_id).lt('mastery_percentage', 60).execute()

        mastered_topics = self.db.table('user_topic_progress').select('*, topics(*)').eq('user_id', user_id).gte('mastery_percentage', 80).execute()

        user_progress = self.db.table('user_progress').select('*').eq('user_id', user_id).execute().data[0]

        return {
            'user_level': user_progress['current_level'],
            'current_question': current_question.data[0] if current_question.data else None,
            'recent_videos': recent_videos.data,
            'weak_topics': weak_topics.data,
            'mastered_topics': mastered_topics.data
        }

    def build_system_prompt(self, context):
        prompt = f"""You are a patient, encouraging math tutor for elementary students.

STUDENT PROFILE:
- Current Level: {context['user_level']} (out of 10)
- Age Estimate: ~{context['user_level'] + 5} years old

CURRENT SITUATION:"""

        if context['current_question']:
            q = context['current_question']
            prompt += f"\n- Working on: {q['question']}"
            prompt += f"\n- Attempts so far: {q.get('attempts', 0)}"

        if context['recent_videos']:
            prompt += "\n\nRECENT VIDEO EXPLANATIONS:"
            for video in context['recent_videos']:
                prompt += f"\n\nVideo for '{video['questions']['question']}':"
                if video.get('explanation_data'):
                    explanation = video['explanation_data']
                    if 'key_terms' in explanation:
                        prompt += f"\nKey Terms Explained: {json.dumps(explanation['key_terms'])}"
                    if 'steps' in explanation:
                        prompt += f"\nSteps Shown: {len(explanation['steps'])} steps"

        if context['weak_topics']:
            topics = [t['topics']['name'] for t in context['weak_topics']]
            prompt += f"\n\nSTRUGGLING WITH: {', '.join(topics)}"

        if context['mastered_topics']:
            topics = [t['topics']['name'] for t in context['mastered_topics']]
            prompt += f"\nGOOD AT: {', '.join(topics)}"

        prompt += """

INSTRUCTIONS:
- Use simple, age-appropriate language
- When student asks about video terms/concepts, reference the explanations above
- Be encouraging and patient
- Break down complex ideas into small steps
- Use examples and analogies"""

        return prompt
```

### 5. VideoService (Enhanced)

**File:** `backend/src/services/video.py`

```python
import json
from anthropic import Anthropic

class VideoService:
    def __init__(self, db_client, anthropic_client, daytona_client):
        self.db = db_client
        self.claude = anthropic_client
        self.daytona = daytona_client

    async def generate_video_with_explanation(self, question_id: str, user_id: str, session_id: str):
        question = self.db.table('questions').select('*').eq('id', question_id).execute().data[0]

        video_record = {
            'question_id': question_id,
            'user_id': user_id,
            'session_id': session_id,
            'status': 'generating'
        }
        video_result = self.db.table('videos').insert(video_record).execute()
        video_id = video_result.data[0]['id']

        try:
            prompt = self.build_dual_generation_prompt(question)

            response = self.claude.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text
            data = self.parse_json_response(content)

            manim_code = data['manim_code']
            explanation_data = data['explanation']

            video_url = await self.execute_manim_in_daytona(manim_code)

            self.db.table('videos').update({
                'status': 'ready',
                'video_url': video_url,
                'manim_code': manim_code,
                'explanation_data': explanation_data
            }).eq('id', video_id).execute()

            self.db.table('user_question_attempts').update({'video_requested': True}).eq('user_id', user_id).eq('question_id', question_id).execute()

            return video_id

        except Exception as e:
            self.db.table('videos').update({
                'status': 'failed',
                'error': str(e)
            }).eq('id', video_id).execute()
            raise

    def build_dual_generation_prompt(self, question):
        return f"""Generate a Manim video explanation for this division problem: {question['question']}

Dividend: {question['dividend']}
Divisor: {question['divisor']}
Answer: {question['correct_answer']}
Remainder: {question['remainder']}

Return JSON with TWO parts:

1. manim_code: Complete Python code for Manim animation
2. explanation: Structured breakdown for teaching

Format:
{{
  "manim_code": "from manim import *\\n\\nclass ExplanationScene(Scene):\\n    def construct(self):\\n        ...",
  "explanation": {{
    "overview": "Brief overview of what we'll learn",
    "steps": [
      {{
        "step_number": 1,
        "action": "What we do in this step",
        "reasoning": "Why we do it this way",
        "key_concept": "Main concept being taught",
        "visual_description": "What appears in the video"
      }}
    ],
    "key_terms": {{
      "quotient": "Simple definition for elementary students",
      "divisor": "Simple definition",
      "dividend": "Simple definition",
      "remainder": "Simple definition (if applicable)"
    }},
    "common_mistakes": ["Mistake 1 students make", "Mistake 2"],
    "difficulty_explanation": "Why this problem is at level {question['difficulty']}"
  }}
}}

Make the explanation age-appropriate for a {question['difficulty'] + 5} year old.
Make the Manim animation clear, colorful, and engaging.
"""

    def parse_json_response(self, text: str):
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

    async def execute_manim_in_daytona(self, manim_code: str):
        pass

    def get_video(self, video_id: str):
        result = self.db.table('videos').select('*').eq('id', video_id).execute()
        return result.data[0] if result.data else None
```

## API Endpoints

### Enhanced `api.py`

```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

@app.get("/users/me/progress")
async def get_user_progress(user_id: str = Depends(get_current_user)):
    return user_progress_service.get_progress(user_id)

@app.get("/users/me/topics/progress")
async def get_user_topics(user_id: str = Depends(get_current_user)):
    return topic_service.get_user_topic_progress(user_id)

@app.get("/topics")
async def get_topics():
    return topic_service.get_all_topics()

@app.get("/topics/{topic_id}")
async def get_topic(topic_id: str):
    topic = topic_service.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic

@app.get("/questions/next")
async def get_next_question(user_id: str = Depends(get_current_user)):
    return question_service.generate_next_question(user_id)

class ValidateAnswerRequest(BaseModel):
    question_id: str
    user_answer: str
    session_id: str

@app.post("/questions/validate")
async def validate_answer(request: ValidateAnswerRequest, user_id: str = Depends(get_current_user)):
    return question_service.validate_answer(user_id, request.question_id, request.user_answer, request.session_id)

class ChatMessageRequest(BaseModel):
    session_id: str
    message: str

@app.post("/chat/messages")
async def send_chat_message(request: ChatMessageRequest, user_id: str = Depends(get_current_user)):
    response = chat_service.send_message(user_id, request.session_id, request.message)
    return {"role": "assistant", "content": response}

@app.get("/chat/context")
async def get_chat_context(session_id: str, user_id: str = Depends(get_current_user)):
    return chat_service.build_chat_context(user_id, session_id)

class GenerateVideoRequest(BaseModel):
    question_id: str
    session_id: str

@app.post("/videos/generate")
async def generate_video(request: GenerateVideoRequest, user_id: str = Depends(get_current_user)):
    video_id = await video_service.generate_video_with_explanation(request.question_id, user_id, request.session_id)
    return {"video_id": video_id}

@app.get("/videos/{video_id}")
async def get_video(video_id: str, user_id: str = Depends(get_current_user)):
    video = video_service.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video

@app.get("/videos/{video_id}/status")
async def get_video_status(video_id: str):
    video = video_service.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return {"status": video['status'], "video_url": video.get('video_url')}
```

## Frontend Integration

### React Hooks

**File:** `frontend/src/hooks/useUserProgress.js`

```javascript
import { useState, useEffect } from 'react';
import api from '../lib/api';

export function useUserProgress() {
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProgress();
  }, []);

  const fetchProgress = async () => {
    try {
      const data = await api.get('/users/me/progress');
      setProgress(data);
    } catch (error) {
      console.error('Failed to fetch progress:', error);
    } finally {
      setLoading(false);
    }
  };

  return { progress, loading, refetch: fetchProgress };
}
```

**File:** `frontend/src/hooks/useTTS.js`

```javascript
import { useState, useEffect, useCallback } from 'react';

export function useTTS() {
  const [speaking, setSpeaking] = useState(false);
  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState(null);
  const [autoplay, setAutoplay] = useState(true);
  const [rate, setRate] = useState(1.0);

  useEffect(() => {
    const loadVoices = () => {
      const availableVoices = speechSynthesis.getVoices();
      setVoices(availableVoices);

      const preferredVoice = availableVoices.find(v => v.lang.startsWith('en-US'));
      setSelectedVoice(preferredVoice || availableVoices[0]);
    };

    loadVoices();
    speechSynthesis.addEventListener('voiceschanged', loadVoices);

    const savedAutoplay = localStorage.getItem('tts_autoplay');
    if (savedAutoplay !== null) {
      setAutoplay(savedAutoplay === 'true');
    }

    const savedRate = localStorage.getItem('tts_rate');
    if (savedRate) {
      setRate(parseFloat(savedRate));
    }

    return () => {
      speechSynthesis.removeEventListener('voiceschanged', loadVoices);
    };
  }, []);

  const speak = useCallback((text) => {
    if (!text) return;

    speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = selectedVoice;
    utterance.rate = rate;

    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);

    speechSynthesis.speak(utterance);
  }, [selectedVoice, rate]);

  const stop = useCallback(() => {
    speechSynthesis.cancel();
    setSpeaking(false);
  }, []);

  const toggleAutoplay = useCallback((value) => {
    setAutoplay(value);
    localStorage.setItem('tts_autoplay', value.toString());
  }, []);

  const changeRate = useCallback((newRate) => {
    setRate(newRate);
    localStorage.setItem('tts_rate', newRate.toString());
  }, []);

  return {
    speak,
    stop,
    speaking,
    voices,
    selectedVoice,
    setSelectedVoice,
    autoplay,
    toggleAutoplay,
    rate,
    changeRate
  };
}
```

**Enhanced:** `frontend/src/hooks/useChat.js`

```javascript
import { useState, useEffect } from 'react';
import api from '../lib/api';
import { useTTS } from './useTTS';

export function useChat(sessionId) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const { speak, autoplay } = useTTS();

  const sendMessage = async (message) => {
    const userMessage = { role: 'user', content: message };
    setMessages(prev => [...prev, userMessage]);

    setLoading(true);
    try {
      const response = await api.post('/chat/messages', {
        session_id: sessionId,
        message: message
      });

      const assistantMessage = { role: 'assistant', content: response.content };
      setMessages(prev => [...prev, assistantMessage]);

      if (autoplay) {
        speak(response.content);
      }
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setLoading(false);
    }
  };

  return { messages, sendMessage, loading };
}
```

## Step-by-Step Implementation

### Step 1: Database Migration

```bash
cd backend
```

Execute SQL in Supabase SQL Editor:

1. Create new tables (user_progress, topics, user_topic_progress, user_question_attempts)
2. Alter existing tables (questions, videos, sessions)
3. Create indexes
4. Insert topic seed data

### Step 2: Backend Services

```bash
cd backend/src/services
```

1. Create `user_progress.py`
2. Create `topics.py`
3. Enhance `questions.py`
4. Enhance `chat.py`
5. Enhance `video.py`

### Step 3: Update API Endpoints

```bash
cd backend/src
```

1. Import new services in `api.py`
2. Initialize service instances
3. Add new endpoints
4. Update existing endpoints

### Step 4: Test Backend

```bash
cd backend
source .venv/bin/activate
fastapi dev src/api.py
```

Test endpoints:
- `GET /users/me/progress`
- `GET /topics`
- `GET /questions/next`
- `POST /questions/validate`
- `POST /chat/messages`

### Step 5: Frontend Hooks

```bash
cd frontend/src/hooks
```

1. Create `useUserProgress.js`
2. Create `useTTS.js`
3. Enhance `useChat.js`
4. Create `useTopics.js` (optional)

### Step 6: Frontend Components

Update components to use new hooks:

1. Add progress display (level, streak)
2. Add TTS controls
3. Show topic mastery
4. Display video explanations with context

### Step 7: Integration Testing

1. Create new user via Clerk
2. Verify user_progress created
3. Request first question (should be Level 1)
4. Validate answer (correct)
5. Check progress update
6. Request video
7. Test chat with video context
8. Test TTS

### Step 8: Deploy

```bash
git add .
git commit -m "Implement user-scoped learning architecture"
git push
```

## Critical Implementation Notes

### Question Deduplication Logic

The `generate_next_question` flow:
1. Get user's current level
2. Get weak topics (mastery < 60%)
3. Query questions matching level + topic
4. Filter out questions in user_question_attempts
5. If none available → generate new with unique signature check

### Level Progression Trigger

Level changes happen in `validate_answer`:
1. Update user_question_attempts
2. Update user_topic_progress (mastery %)
3. Call `calculate_next_level`
4. Update user_progress if level changed

### Chat Context Building

Context is built on-the-fly for each message:
1. Current question (from session)
2. Last 3 videos (with explanation_data JSONB)
3. Weak topics (mastery < 60%)
4. Mastered topics (mastery >= 80%)
5. User level

### Video Dual Generation

Single Claude call returns:
```json
{
  "manim_code": "...",
  "explanation": {
    "steps": [...],
    "key_terms": {...},
    "common_mistakes": [...],
    "difficulty_explanation": "..."
  }
}
```

Store both in videos table. Frontend accesses explanation for context.

## Performance Considerations

1. **Index all foreign keys** - user_id, question_id, topic_id, session_id
2. **Cache user_progress** - Don't fetch on every question
3. **Limit video context** - Only last 3 videos to reduce JSONB transfer
4. **Use connection pooling** - Supabase client with connection pool
5. **Batch updates** - Update user_progress, user_topic_progress in transaction

## Security Considerations

1. **Row Level Security (RLS)** - Enable on all tables
2. **User isolation** - All queries filter by authenticated user_id
3. **Video URL expiration** - Supabase signed URLs with 1-day TTL
4. **Rate limiting** - Limit video generation to prevent abuse
5. **Input validation** - Pydantic models for all API requests

## Monitoring & Analytics

Track:
1. User progress over time (level changes, streak)
2. Topic mastery distribution
3. Question attempt patterns
4. Video generation success rate
5. Chat context effectiveness (user satisfaction)

## Future Enhancements

1. **Adaptive difficulty** - Adjust question difficulty within level based on performance
2. **Personalized explanations** - Tailor video explanations to user's weak areas
3. **Spaced repetition** - Resurface old topics to prevent forgetting
4. **Gamification** - Badges, achievements, leaderboards
5. **Parent dashboard** - Progress reports, insights
6. **Multi-topic support** - Expand beyond division (multiplication, fractions, etc.)
7. **Standards alignment** - Map to Common Core, state standards
8. **Premium TTS** - ElevenLabs for natural voices
9. **Offline mode** - Download questions for practice without internet
10. **Collaborative learning** - Group challenges, peer explanations
