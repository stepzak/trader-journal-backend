import datetime

from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    username: str


class TokenModel(BaseModel):
    access_token: str
    refresh_token: str


class UserPutDTO(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    bio: str | None = None
    url_image: str | None = None


class UserGetDTO(UserPutDTO):
    guid: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


class UserPublicDTO(UserPutDTO):
    created_at: datetime.datetime


class ApiKeys(BaseModel):
    api_key: str
    secret_key: str
    key_type: str