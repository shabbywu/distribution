from typing import Optional

import requests


class RequestError(Exception):
    """Base Exception for requests"""

    def __init__(self, message: str, status_code):
        self.message = message
        super().__init__(message, status_code)


class RequestErrorWithResponse(RequestError):
    """Request error with requests.Response"""

    def __init__(self, message: str, status_code, response: Optional[requests.Response] = None):
        super().__init__(message, status_code)
        self.response = response


class AuthFailed(RequestErrorWithResponse):
    """Auth Failed for registry"""


class RetryAgain(Exception):
    """Dummy Exception to mark retry"""


class PermissionDeny(Exception):
    """Permission deny for endpoints or resources"""


class ResourceNotFound(Exception):
    """Resources not found."""


class UnSupportMediaType(Exception):
    """raise when the media type is unsupported"""
