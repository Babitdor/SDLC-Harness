from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class AskQuestionInput(BaseModel):
    """Input schema for `ask_question`."""

    question: str = Field(
        ...,
        description="The clarifying question to ask the user to resolve ambiguities."
    )
    options: list[str] = Field(
        default=[],
        description="Optional list of multiple choice options (strings) for the user to pick from."
    )

class AskQuestionTool(BaseTool):
    """Tool for asking the user clarifying questions."""

    name: str = "ask_question"
    description: str = (
        "Ask the user a clarifying question when you need more information "
        "or context to complete the plan or task. Use the optional options list "
        "to provide multiple-choice choices (MCQ style) if the user needs to select from "
        "pre-defined options. The run will pause and display the question and choices. "
        "You MUST stop generating and wait for the user's response."
    )
    args_schema: type[BaseModel] = AskQuestionInput

    def _run(self, question: str, options: list[str] = []) -> str:
        options_str = f" Options: {options}" if options else ""
        return (
            f"QUESTION ASKED: '{question}'{options_str}\n"
            "Your question has been presented to the user. Please stop generating "
            "and wait for their response."
        )

def build_ask_question_tools() -> list[BaseTool]:
    """Construct the ask-question tool for the orchestrator."""
    return [AskQuestionTool()]
