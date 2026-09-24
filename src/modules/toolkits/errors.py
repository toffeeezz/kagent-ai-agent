from modules.errors import ProgramError


class ToolKitError(ProgramError):
    kit_name: str | None

    def __init__(self, message: str, kit_name: str | None, *args: object) -> None:
        super().__init__(message, *args)
        self.kit_name = kit_name


class ToolKitNotFoundError(ToolKitError):
    def __init__(self, kit_name: str | None, *args: object) -> None:
        super().__init__(f"No such thing as {kit_name} toolkit", kit_name, *args)


class ToolExecutionError(ToolKitError):
    tool_name: str | None

    def __init__(
        self, message: str, kit_name: str | None, tool_name: str | None, *args: object
    ) -> None:
        super().__init__(message, kit_name, *args)
        self.tool_name = tool_name
