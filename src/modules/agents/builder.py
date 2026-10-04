import logging
from pathlib import Path

import frontmatter
import yaml
from pydantic import ValidationError

from modules.agents.models import AgentDefinition, BasicAgent, CompleteAgent
from modules.errors import ProgramError
from modules.toolkits.registry import REGISTRY

AGENTS_DIR = Path(__file__).resolve().parent
AGENT_DEFINITION_DIR = AGENTS_DIR / "definitions"
GLOBAL_SYSTEM_PROMPT = AGENTS_DIR / "GLOBAL_SYSTEM_PROMPT.md"
AGENT_AVATAR_DIR = AGENTS_DIR / "avatars"

logger = logging.getLogger(__name__)


def _build_agent(
    definition: AgentDefinition, system_prompt: str
) -> CompleteAgent | BasicAgent:
    if definition.type == "basic":
        return BasicAgent(
            name=definition.name,
            language_model=definition.language_model,
            system_prompt=system_prompt,
            params=definition.params,
        )
    else:
        return CompleteAgent(
            name=definition.name,
            language_model=definition.language_model,
            params=definition.params,
            registry=REGISTRY,
            system_prompt=f"{GLOBAL_SYSTEM_PROMPT.read_text()}\n{system_prompt}",
            max_loops=definition.max_loop if definition.max_loop else 40,
        )


def scan_agent_dir() -> tuple[
    dict[str, BasicAgent], dict[str, CompleteAgent], list[AgentDefinition]
]:
    if not AGENT_DEFINITION_DIR.exists():
        logger.error(
            "Agent definitions directory is missing. Expected: %s", AGENT_DEFINITION_DIR
        )
        raise ProgramError(
            f"Agent definitions directory is missing: {AGENT_DEFINITION_DIR}"
        )

    if not GLOBAL_SYSTEM_PROMPT.exists():
        logger.error(
            "Agent global system prompt markdown is missing. Expected: %s",
            GLOBAL_SYSTEM_PROMPT,
        )
        raise ProgramError(
            f"Agents global system prompt is missing: {GLOBAL_SYSTEM_PROMPT}"
        )

    basic_agents: dict[str, BasicAgent] = {}
    complete_agents: dict[str, CompleteAgent] = {}
    agent_definitions: list[AgentDefinition] = []

    for file in sorted(AGENT_DEFINITION_DIR.iterdir(), key=lambda p: p.name.lower()):
        print(file.name)
        if not file.is_file():
            logger.warning("Ignoring a non-file in the directoy: %s", file.name)
            continue
        if file.suffix != ".md":
            logger.warning("Ignoring a non-markdown file: %s", file.name)
            continue

        try:
            post = frontmatter.load(file)
            definition = AgentDefinition.model_validate(post.metadata)
            prompt = post.content

            agent = _build_agent(definition, prompt)
            agent_definitions.append(definition)
            if isinstance(agent, BasicAgent):
                basic_agents[agent.name] = agent
            else:
                complete_agents[agent.name] = agent

        except yaml.YAMLError:
            logger.warning(
                "Ignoring a definition with an invalid yaml syntax: %s", file.name
            )
            continue
        except ValidationError as e:
            logger.warning(
                "Ignoring a definition with an invalid parameter in params: %s -> %s",
                file.name,
                e,
            )
            continue
        except Exception as e:
            logger.warning(
                "An unexpected exception occured while scanning %s: %s",
                file.name,
                e,
            )
            continue

    return basic_agents, complete_agents, agent_definitions
