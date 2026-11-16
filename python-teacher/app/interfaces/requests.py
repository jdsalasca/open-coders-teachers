"""Esquemas de entrada validados con Pydantic."""

from pydantic import BaseModel, ConfigDict, Field


class CreateTaskRequest(BaseModel):
    """Payload de creacion de tarea."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
