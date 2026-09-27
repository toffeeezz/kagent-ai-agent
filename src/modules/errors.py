class ProgramError(Exception):
    message: str

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(*args)
        self.message = message
