"""Placeholder repository for refresh tokens.

This module will evolve in upcoming slices.  For now it defines the class
signature that the service layer will depend on so tests and initial code can
import it without error.
"""


class TokenRepository:
    def __init__(self) -> None:
        # real implementation will accept a session/engine
        pass

    def create_refresh_token(self, user_id: str, token_hash: str, expires_at: str) -> None:
        raise NotImplementedError

    def revoke_token(self, token_id: str) -> None:
        raise NotImplementedError

    def get_token(self, token_id: str) -> dict | None:
        raise NotImplementedError
