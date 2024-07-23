import datetime

from pydantic import BaseModel

from schemas.auth_schema import UserGetDTO, UserPublicDTO


class MessageModel(BaseModel):
    id: int
    content: str
    user: UserPublicDTO
    created_at: datetime.datetime