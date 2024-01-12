from datetime import datetime

from src._types import BaseModel


class AccessToken(BaseModel):
    token_type: str = "Bearer"
    access_token: str
    expires_at: datetime
    issued_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime
    refresh_token_issued_at: datetime
