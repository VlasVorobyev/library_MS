from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Boolean, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    loans = relationship("Loan", back_populates="user")
    ratings = relationship("Rating", back_populates="user")

    role = Column(String, default="user")  # "admin" или "user"


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    author = Column(String, index=True, nullable=False)
    genre = Column(String, index=True, nullable=False)
    year = Column(Integer, nullable=False)
    available_copies = Column(Integer, default=1)
    total_copies = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    loans = relationship("Loan", back_populates="book")
    ratings = relationship("Rating", back_populates="book")


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    loan_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime, nullable=True)
    status = Column(String, default="active")

    user = relationship("User", back_populates="loans")
    book = relationship("Book", back_populates="loans")


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    score = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ratings")
    book = relationship("Book", back_populates="ratings")