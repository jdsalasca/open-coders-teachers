"""Esquemas de entrada validados con Pydantic."""

from pydantic import BaseModel, Field, field_validator


class CreateTaskRequest(BaseModel):
    """Payload de creacion de tarea."""

    title: str = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        """Rechaza un titulo que solo tiene espacios."""
        if not value.strip():
            raise ValueError("el titulo no puede estar vacio")
        return value
