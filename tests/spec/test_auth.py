from moby_distribution.spec.auth import TokenResponse


def test_auth(auth_response):
    return TokenResponse(**auth_response).dict(exclude_unset=True) == auth_response
