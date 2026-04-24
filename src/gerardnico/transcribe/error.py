class AppError(Exception):
    def __init__(self, message: str, code: int | str  = 1):
        super().__init__(message)
        self.code = code
