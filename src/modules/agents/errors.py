from modules.errors import ProgramError


class AgentError(ProgramError):
    name: str

    def __init__(self, message: str, name: str, *args: object) -> None:
        super().__init__(message, *args)
        self.name = name
