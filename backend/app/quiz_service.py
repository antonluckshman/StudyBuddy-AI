import json
import re
from typing import Any
import httpx


class QuizGenerationError(Exception):
    pass


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\\s*```$", "", text)
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            value = json.loads(text[start:end + 1])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass
    raise QuizGenerationError("The model did not return valid quiz JSON. Please try again.")


def validate_quiz(payload: dict[str, Any], count: int) -> dict[str, Any]:
    questions = []
    raw_questions = payload.get("questions")
    if not isinstance(raw_questions, list):
        raise QuizGenerationError("The model response did not contain a questions list.")
    for item in raw_questions:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        options = item.get("options")
        explanation = str(item.get("explanation", "")).strip()
        excerpt = str(item.get("source_excerpt", "")).strip()
        try:
            correct_index = int(item.get("correct_index"))
        except (ValueError, TypeError):
            continue
        if not question or not isinstance(options, list) or len(options) != 4:
            continue
        options = [str(x).strip() for x in options]
        if any(not x for x in options) or len(set(x.casefold() for x in options)) != 4:
            continue
        if correct_index not in range(4) or not explanation:
            continue
        questions.append({
            "question": question,
            "options": options,
            "correct_index": correct_index,
            "explanation": explanation,
            "source_excerpt": excerpt[:500],
        })
    if len(questions) < min(3, count):
        raise QuizGenerationError("The model returned too few valid questions. Try shorter notes or generate again.")
    return {
        "title": str(payload.get("title", "Your practice quiz")).strip()[:100] or "Your practice quiz",
        "questions": questions[:count],
    }


async def generate_quiz(notes: str, question_count: int, difficulty: str, topic: str, base_url: str, model: str):
    focus = f"Focus on this topic if covered: {topic}." if topic else "Cover the main ideas across the notes."
    prompt = f"""
You are a careful study coach. Create a multiple-choice quiz using ONLY the notes below.
Difficulty: {difficulty}. Generate {question_count} questions. {focus}
Return ONLY a JSON object in this format:
{{
  "title": "Short quiz title",
  "questions": [
    {{
      "question": "Question text",
      "options": ["A", "B", "C", "D"],
      "correct_index": 0,
      "explanation": "Why the correct answer is supported by the notes",
      "source_excerpt": "Short phrase copied from the notes"
    }}
  ]
}}
Rules: exactly four distinct options; correct_index is 0-3; one correct answer; concise explanation; do not invent facts; do not include markdown or text outside JSON.

STUDY NOTES:
<notes>
{notes}
</notes>
"""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=5.0)) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False, "format": "json",
                      "options": {"temperature": 0.2}},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.ConnectError as exc:
        raise QuizGenerationError("Could not connect to Ollama. Start Ollama and check OLLAMA_BASE_URL.") from exc
    except httpx.TimeoutException as exc:
        raise QuizGenerationError("The model took too long. Try fewer questions or a smaller model.") from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise QuizGenerationError(f"Model '{model}' was not found. Run `ollama pull {model}`.") from exc
        raise QuizGenerationError(f"Ollama returned HTTP {exc.response.status_code}.") from exc
    except (ValueError, KeyError) as exc:
        raise QuizGenerationError("Ollama returned an unreadable response.") from exc
    if not data.get("response"):
        raise QuizGenerationError("Ollama returned an empty response. Try again.")
    return validate_quiz(extract_json(data["response"]), question_count)
