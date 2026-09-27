from enum import StrEnum
from typing import Any

from modules.agents.models import BaseAgent
from modules.agents.orchestrator.agent import ORCHESTRATOR_AGENT
from modules.agents.summarizer.agent import SUMMARIZER_AGENT

DEFAULT_MODEL: str = "deepseek/deepseek-v4-flash"

AGENTS: dict[str, BaseAgent[Any, Any, Any]] = {
    ORCHESTRATOR_AGENT.name: ORCHESTRATOR_AGENT,
    SUMMARIZER_AGENT.name: SUMMARIZER_AGENT,
}


class AgentEnum(StrEnum):
    ORCHESTRATOR = ORCHESTRATOR_AGENT.name
    SUMMARIZER = SUMMARIZER_AGENT.name
