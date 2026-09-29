class DomainError(Exception):
    def __init__(self, message, code="conflict", status=409):
        self.message, self.code, self.status = message, code, status
        super().__init__(message)
