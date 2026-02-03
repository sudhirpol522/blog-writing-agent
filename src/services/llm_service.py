"""LLM service for interacting with language models."""

from __future__ import annotations

import os
from typing import List, Type, TypeVar

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """Service for managing LLM interactions."""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.7):
        """Initialize LLM service.

        Args:
            model: Model name to use
            temperature: Temperature for generation
        """
        self.model = model
        self.temperature = temperature
        self._llm = None

    @property
    def llm(self) -> ChatOpenAI:
        """Get or create LLM instance."""
        if self._llm is None:
            self._llm = ChatOpenAI(model=self.model, temperature=self.temperature)
        return self._llm

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        """Invoke LLM with prompts.

        Args:
            system_prompt: System message content
            user_prompt: User message content

        Returns:
            Generated text
        """
        response = self.llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        return response.content.strip()

    def invoke_structured(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        schema: Type[T]
    ) -> T:
        """Invoke LLM with structured output.

        Args:
            system_prompt: System message content
            user_prompt: User message content
            schema: Pydantic model for structured output

        Returns:
            Structured response
        """
        structured_llm = self.llm.with_structured_output(schema)
        return structured_llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
