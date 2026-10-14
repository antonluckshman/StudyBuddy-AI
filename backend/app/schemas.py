from typing import Literal
from pydantic import BaseModel, Field, field_validator


class QuizRequest(BaseModel):
    notes: str = Field(min_length=40, max_length=100000)
    question_count: int = Field(default=5, ge=3, le=10)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    topic: str = Field(default="", max_length=120)

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 40:
            raise ValueError("Please provide at least 40 characters of notes.")
        return value

    @field_validator("topic")
    @classmethod
    def clean_topic(cls, value: str) -> str:
        return value.strip()


class QuizQuestion(BaseModel):
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str
    source_excerpt: str = ""


class QuizResponse(BaseModel):
    title: str
    questions: list[QuizQuestion]
    model: str
    note: str = "AI-generated answers may be imperfect. Check important answers against your notes."


class HealthResponse(BaseModel):
    status: str
    ollama_reachable: bool
    model: str
    detail: str
