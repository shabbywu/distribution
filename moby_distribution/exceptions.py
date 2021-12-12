import requests


class RequestError(Exception):
    """Base Exception for requests"""

    def __init__(self, message: str, status_code):
        self.message = message
        super().__init__(message, status_code)


class RequestErrorWithResponse(RequestError):
    """Request error with requests.Response"""

    def __init__(self, message: str, status_code, response: requests.Response):
        super().__init__(message, status_code)
        self.response = response


class AuthFailed(RequestErrorWithResponse):
    """Auth Failed for registry"""


class RetryAgain:
    """Dummy Exception to mark retry"""


class PermissionDeny:
    """Permission deny for endpoints or resources"""


class ResourceNotFound:
    """Resources not found."""