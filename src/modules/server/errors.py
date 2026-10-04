from modules.agents.errors import AgentError


class ServerRequestError(AgentError):
    def __init__(self, name: str, message: str, *args: object) -> None:
        super().__init__(message, name, *args)


class LLMRequestError(ServerRequestError):
    pass


class EmbeddingRequestError(ServerRequestError):
    pass
