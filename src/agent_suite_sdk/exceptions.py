class AgentSuiteError(Exception):
    """Base exception for Agent Suite SDK."""
    pass

class APIError(AgentSuiteError):
    """Exception raised for API errors."""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code
