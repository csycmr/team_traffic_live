"""서비스 계층 오류. Flask와 FastAPI가 각자 JSON 응답으로 바꾼다."""


class ServiceError(Exception):
    """상태 코드와 사용자용 메시지를 가진 오류. 응답 본문은 {"error": 메시지, **extra}."""

    def __init__(self, message: str, status_code: int = 500, **extra):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.extra = extra

    def payload(self) -> dict:
        return {"error": self.message, **self.extra}
