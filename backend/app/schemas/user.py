from pydantic import BaseModel, Field


class UserBase(BaseModel):
    username: str
    email: str
    role: str = "member"

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int
    is_active: bool


class UserPublic(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool = True


class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: str = Field(min_length=5, max_length=128)
    password: str = Field(min_length=8, max_length=128)
    role: str = "member"


class UserLoginRequest(BaseModel):
    identity: str
    password: str


class UserTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class UserResetPasswordRequest(BaseModel):
    old_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
