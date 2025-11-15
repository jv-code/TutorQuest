# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered teaching assistant application for long division practice. The application uses Claude API for question generation and answer validation, and generates educational Manim videos via Daytona when students struggle with problems.

**Frontend**: React 19 + Vite with Tailwind CSS and shadcn/ui components
**Backend**: FastAPI (Python 3.13) with Claude Haiku 4.5 and Sonnet 4.5 integration
**Database**: Supabase (PostgreSQL + Storage)
**Video Generation**: Daytona sandboxes for executing Manim code

## Development Commands

### Frontend Development
```bash
cd frontend
npm install                    # Install dependencies
npm run dev                    # Start dev server on http://localhost:5173
npm run build                  # Build production bundle
npm run lint                   # Run ESLint
```

### Backend Development
```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate      # macOS/Unix

# Install dependencies
pip install -r requirements.txt

# Run API server
fastapi dev src/api.py         # Runs on http://127.0.0.1:8000
```

### Full-Stack Development
Run both servers concurrently:
1. Terminal 1: `cd backend && source .venv/bin/activate && fastapi dev src/api.py`
2. Terminal 2: `cd frontend && npm run dev`

The Vite dev server proxies `/api/*` requests to the backend server at `http://127.0.0.1:8000`.

### Required Environment Variables
Create `backend/.env` with:
```
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
DAYTONA_API_KEY=dtn_...
DAYTONA_API_URL=https://app.daytona.io/api
```

## Architecture

### Question Flow
1. **Question Generation**: Claude Haiku 4.5 generates difficulty-scaled long division problems
2. **Answer Validation**: Claude Haiku 4.5 validates student answers
3. **Feedback Strategy**:
   - Attempts 1-2: Generic "Incorrect. Please try again." message
   - Attempt 3: Detailed feedback + video offer button
4. **Video Generation** (on-demand only):
   - Claude Sonnet 4.5 generates Manim Python code
   - Daytona sandbox executes code and renders video
   - Video uploaded to Supabase Storage
   - Frontend polls status every 2 seconds until complete

### Backend Structure

**Prompt Management** (`backend/src/prompts/`):
- Uses Jinja2 templates for all AI prompts
- `generate_question.j2`: Question generation with difficulty scaling
- `validate_answer.j2`: Answer validation
- `generate_manim.j2`: Manim code generation for videos

**Services** (`backend/src/services/`):
- `chat.py`: Claude Haiku 4.5 for questions, validation, and chat
- `video.py`: Claude Sonnet 4.5 + Daytona for video generation
- `questions.py`: Question flow logic and attempt tracking

**Data Models** (`backend/src/models/schemas.py`):
- Pydantic models with strict validation
- `AnswerValidationResponse` includes `offer_video` flag after 3 attempts

**Database** (`backend/src/db/supabase.py`):
- Tables: `sessions`, `messages`, `questions`, `videos`
- Storage bucket: `videos` (1-day retention policy)

### Frontend Structure

**State Management** (`frontend/src/hooks/useChat.js`):
- Manages question flow, validation, and video generation
- `offerVideo` state triggers video offer UI after 3rd failed attempt
- `requestVideo()` initiates on-demand video generation
- `pollVideoStatus()` monitors video rendering progress

**UI Components** (`frontend/src/components/`):
- `QuestionCard`: Displays question with color-coded attempt tracking
- `AnswerInput`: Text input for student answers
- `ChatMessage`: Renders feedback with markdown + KaTeX math
- Video offer card: Purple gradient card that appears after 3 failed attempts

**Styling**:
- Tailwind CSS with gradient backgrounds (blue-to-indigo theme)
- shadcn/ui components for cards, buttons, inputs, scroll areas
- KaTeX for LaTeX math rendering in feedback

### API Endpoints

**Sessions**:
- `POST /sessions` - Create new session
- `GET /messages/{session_id}` - Get chat history

**Questions**:
- `GET /questions/next?session_id=` - Generate next question (auto-scaled difficulty)
- `POST /questions/validate` - Validate answer, returns feedback + `offer_video` flag

**Messages**:
- `POST /messages` - Send chat message to teaching assistant

**Videos**:
- `POST /videos/generate` - Generate video for question (user-initiated only)
- `GET /videos/{video_id}/status` - Poll video generation status
- `GET /videos/{video_id}` - Get completed video URL

## Key Implementation Details

### Claude Model Selection
- **Haiku 4.5** (`claude-haiku-4-5-20251001`): Fast, cost-effective for questions/validation/chat
- **Sonnet 4.5** (`claude-sonnet-4-5-20250929`): Superior code generation for Manim scripts

### Difficulty Progression
Questions auto-scale based on completed count:
- Level 1-3: Simple divisions (2-digit ÷ 1-digit, e.g., 48 ÷ 6)
- Level 4-6: Medium divisions (3-digit ÷ 1-digit or 2-digit ÷ 2-digit)
- Level 7-10: Complex divisions (3-digit ÷ 2-digit or 4-digit ÷ 2-digit)

Formula: `difficulty = min(1 + completed_count // 2, 10)`

### JSON Response Parsing
Claude responses are stripped of markdown code blocks before JSON parsing:
```python
text = response.content[0].text.strip()
if text.startswith("```json"):
    text = text[7:]
if text.startswith("```"):
    text = text[3:]
if text.endswith("```"):
    text = text[:-3]
return json.loads(text.strip())
```

### Daytona Video Generation Flow
1. Generate Manim code via Claude Sonnet 4.5
2. Create Daytona sandbox
3. Install manim library
4. Write code to `scene.py`
5. Execute `manim -ql scene.py ExplanationScene`
6. Find and base64-encode output MP4
7. Upload to Supabase Storage
8. Return public URL
9. Delete sandbox

### Vite Proxy Configuration
Development proxy forwards `/api/*` to backend (`frontend/vite.config.js:30-34`):
```js
proxy: {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, '')
  }
}
```

## Adding Dependencies

**Python**: Add to `backend/requirements.txt`, then:
```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
```

**JavaScript**:
```bash
cd frontend
npm install <package>
```

## Database Setup

Required Supabase tables (create via SQL editor):
```sql
-- Sessions table
CREATE TABLE sessions (
  id UUID PRIMARY KEY,
  created_at TIMESTAMP WITH TIME ZONE
);

-- Messages table
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID REFERENCES sessions(id),
  role TEXT,
  content TEXT,
  created_at TIMESTAMP WITH TIME ZONE
);

-- Questions table
CREATE TABLE questions (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  question TEXT,
  topic TEXT,
  difficulty INTEGER,
  attempts INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE
);

-- Videos table
CREATE TABLE videos (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  question_id UUID REFERENCES questions(id),
  status TEXT,
  video_url TEXT,
  error TEXT,
  created_at TIMESTAMP WITH TIME ZONE
);
```

Create Supabase Storage bucket named `videos` with public access and 1-day retention policy.
