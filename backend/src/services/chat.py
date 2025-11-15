import anthropic
import json
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
try:
    import config
    from config import settings
except ModuleNotFoundError:
    from src.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

prompts_dir = Path(__file__).parent.parent / "prompts"
env = Environment(
    loader=FileSystemLoader(prompts_dir),
    autoescape=select_autoescape()
)

def generate_next_question(topic: str, difficulty: int, previous_questions: list[str] = []) -> dict:
    template = env.get_template("generate_question.j2")
    prompt = template.render(
        difficulty=difficulty,
        previous_questions=previous_questions[:5]
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": f"You are a mathematics teaching assistant. Generate educational questions.\n\n{prompt}"}
        ]
    )

    text = response.content[0].text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Find first valid JSON object in case of extra content
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Try to extract just the JSON object portion
        lines = text.split('\n')
        for i in range(len(lines)):
            try:
                # Try parsing from this line onwards
                partial = '\n'.join(lines[i:])
                result = json.loads(partial)
                return result
            except:
                continue
        # If that fails, try to find JSON between curly braces
        start_idx = text.find('{')
        if start_idx != -1:
            # Find matching closing brace
            brace_count = 0
            for i in range(start_idx, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        try:
                            return json.loads(text[start_idx:i+1])
                        except:
                            pass
        raise e

def validate_answer(question: str, user_answer: str, correct_context: str = "") -> dict:
    template = env.get_template("validate_answer.j2")
    prompt = template.render(
        question=question,
        user_answer=user_answer
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": f"You are a mathematics teaching assistant. Evaluate answers fairly and provide constructive feedback.\n\n{prompt}"}
        ]
    )

    text = response.content[0].text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Find first valid JSON object in case of extra content
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Try to extract just the JSON object portion
        lines = text.split('\n')
        for i in range(len(lines)):
            try:
                # Try parsing from this line onwards
                partial = '\n'.join(lines[i:])
                result = json.loads(partial)
                return result
            except:
                continue
        # If that fails, try to find JSON between curly braces
        start_idx = text.find('{')
        if start_idx != -1:
            # Find matching closing brace
            brace_count = 0
            for i in range(start_idx, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        try:
                            return json.loads(text[start_idx:i+1])
                        except:
                            pass
        raise e

def generate_hint(question: str, user_answer: str) -> str:
    template = env.get_template("generate_hint.j2")
    prompt = template.render(question=question, user_answer=user_answer)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    text = response.content[0].text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        result = json.loads(text)
        return result.get("hint", "Try breaking down the problem into smaller steps.")
    except:
        return "Try breaking down the problem into smaller steps."

def chat_response(messages: list[dict]) -> str:
    system_msg = "You are a helpful mathematics teaching assistant specializing in long division. Help students understand the step-by-step process, explain remainders, and guide them through solving division problems. Answer questions clearly and concisely."

    claude_messages = []
    for msg in messages:
        if msg["role"] != "system":
            claude_messages.append(msg)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=system_msg,
        messages=claude_messages
    )

    return response.content[0].text
