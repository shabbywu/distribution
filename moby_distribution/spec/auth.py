import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Token Response
    spec: https://github.com/distribution/distribution/blob/main/docs/spec/auth/token.md#token-response-fields

    """

    token: str = Field(
        ...,
        description="An opaque Bearer token that clients should "
        "supply to subsequent requests in the Authorization header.",
    )
    access_token: Optional[str] = Field(
        None,
        description="For compatibility with OAuth 2.0, we will also accept token under the name access_token",
    )
    issued_at: Optional[datetime.datetime] = Field(
        None,
        description="The RFC3339-serialized UTC standard time at which a given token was issued.",
    )
    expires_in: Optional[int] = Field(
        None,
        description="The duration in seconds since the token was issued that it will remain valid. ",
    )
    refresh_token: Optional[str] = Field(
        None,
        description="Token which can be used to get additional access tokens "
        "for the same subject with different scopes. ",
    )
