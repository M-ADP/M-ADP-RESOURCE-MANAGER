from typing import Optional


class AppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        detail: Optional[dict] = None
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)
