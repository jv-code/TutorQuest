import anthropic
import uuid
import base64
import json
from datetime import datetime, timedelta, timezone
from daytona import Daytona, DaytonaConfig
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
try:
    import config
    from config import settings
    from db.supabase import supabase
except ModuleNotFoundError:
    from src.config import settings
    from src.db.supabase import supabase

haiku_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
sonnet_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

prompts_dir = Path(__file__).parent.parent / "prompts"
env = Environment(
    loader=FileSystemLoader(prompts_dir),
    autoescape=select_autoescape()
)

def generate_explanation(question: str) -> str:
    template = env.get_template("explain_solution.j2")
    prompt = template.render(question=question)

    message = haiku_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    text = message.content[0].text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    result = json.loads(text.strip())
    return result["explanation"]

def generate_manim_code(question: str, explanation: str) -> str:
    template = env.get_template("generate_manim.j2")
    prompt = template.render(question=question, explanation=explanation)

    message = sonnet_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )

    code = message.content[0].text.strip()
    if code.startswith("```python"):
        code = code[9:]
    if code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    return code.strip()

def get_or_generate_code(question: str) -> str:
    explanation = generate_explanation(question)
    return generate_manim_code(question, explanation)

def execute_manim_code(manim_code: str) -> tuple[bytes, str]:
    from daytona import CreateSandboxFromSnapshotParams

    config = DaytonaConfig(
        api_key=settings.daytona_api_key,
        api_url=settings.daytona_api_url
    )
    daytona = Daytona(config)

    params = CreateSandboxFromSnapshotParams(snapshot="manim-voiceover-v4")
    sandbox = daytona.create(params)

    code_safe = manim_code.encode('ascii', errors='ignore').decode('ascii')
    code_b64 = base64.b64encode(code_safe.encode()).decode()
    write_result = sandbox.process.exec(f"echo '{code_b64}' | base64 -d > scene.py")

    verify_result = sandbox.process.exec("wc -l scene.py && head -5 scene.py")

    render_result = sandbox.process.exec("python3 -m manim -ql scene.py ExplanationScene 2>&1")

    video_path_result = sandbox.process.exec("find media -name 'ExplanationScene.mp4' -type f 2>/dev/null")
    video_path = video_path_result.result.strip()

    if not video_path:
        raise Exception(f"Video not found. Code verify: {verify_result.result[:200]}. Render: {render_result.result[:1000]}")

    video_content_result = sandbox.process.exec(f"cat {video_path} | base64 | tr -d '\\n'")
    video_base64 = video_content_result.result.strip()
    video_base64_clean = ''.join(c for c in video_base64 if c.isalnum() or c in '+/=')

    video_bytes = base64.b64decode(video_base64_clean)

    sandbox.delete()

    return video_bytes, render_result.result

def upload_to_supabase(video_bytes: bytes, video_id: str) -> str:
    file_path = f"{video_id}.mp4"

    supabase.storage.from_('videos').upload(
        file_path,
        video_bytes,
        {'content-type': 'video/mp4', 'x-upsert': 'true'}
    )

    public_url = supabase.storage.from_('videos').get_public_url(file_path)

    return public_url

def cleanup_old_videos() -> dict:
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=1)
    videos = supabase.storage.from_('videos').list()
    old_videos = [
        video['name'] for video in videos
        if datetime.fromisoformat(video['created_at'].replace('Z', '+00:00')) < cutoff_time
    ]
    if old_videos:
        supabase.storage.from_('videos').remove(old_videos)
    return {"deleted": len(old_videos), "files": old_videos}

def generate_video(question: str) -> dict:
    video_id = str(uuid.uuid4())

    try:
        manim_code = get_or_generate_code(question)
        video_bytes, render_log = execute_manim_code(manim_code)
        video_url = upload_to_supabase(video_bytes, video_id)

        return {
            "video_id": video_id,
            "status": "completed",
            "video_url": video_url,
            "error": None
        }
    except Exception as e:
        return {
            "video_id": video_id,
            "status": "failed",
            "video_url": None,
            "error": str(e)
        }
