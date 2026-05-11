from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role: str = Field(default="user", pattern="^(user|admin)$")


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    role: str

    class Config:
        orm_mode = True


class BookBase(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    genre: str = Field(..., min_length=1)
    year: int = Field(..., ge=1000, le=datetime.now().year)
    total_copies: int = Field(default=1, ge=1)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[int] = None
    total_copies: Optional[int] = None


class BookResponse(BookBase):
    id: int
    available_copies: int
    created_at: datetime

    class Config:
        orm_mode = True


class LoanBase(BaseModel):
    book_id: int


class LoanCreate(LoanBase):
    pass


class LoanReturn(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)


class LoanResponse(LoanBase):
    id: int
    user_id: int
    loan_date: datetime
    due_date: datetime
    return_date: Optional[datetime]
    status: str
    book: Optional[BookResponse]

    class Config:
        orm_mode = True


class RatingCreate(BaseModel):
    book_id: int
    score: int = Field(..., ge=1, le=5)


class RatingResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    score: int
    created_at: datetime

    class Config:
        orm_mode = True


class BookRecommendation(BaseModel):
    book_id: int
    title: str
    author: str
    genre: str
    year: int
    similarity_score: float
    avg_rating: float


class Token(BaseModel):
    access_token: str
    token_type: str


class MessageResponse(BaseModel):
    message: str