"""CRUD операции для работы с базой данных"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas


def create_user(db: Session, user: schemas.UserCreate, hashed_password: str):
    """Создание нового пользователя"""
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_username(db: Session, username: str):
    """Получение пользователя по имени"""
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str):
    """Получение пользователя по email"""
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    """Получение пользователя по ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_book(db: Session, book: schemas.BookCreate):
    """Создание новой книги"""
    db_book = models.Book(
        title=book.title,
        author=book.author,
        genre=book.genre,
        year=book.year,
        total_copies=book.total_copies,
        available_copies=book.total_copies
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


def get_book(db: Session, book_id: int):
    """Получение книги по ID"""
    return db.query(models.Book).filter(models.Book.id == book_id).first()


def get_all_books(db: Session, skip: int = 0, limit: int = 100):
    """Получение списка всех книг"""
    return db.query(models.Book).offset(skip).limit(limit).all()


def get_books_by_genre(db: Session, genre: str, skip: int = 0, limit: int = 100):
    """Получение книг по жанру"""
    return db.query(models.Book).filter(
        models.Book.genre == genre
    ).offset(skip).limit(limit).all()


def update_book(db: Session, book_id: int, book_update: schemas.BookUpdate):
    """Обновление информации о книге"""
    db_book = get_book(db, book_id)
    if db_book:
        update_data = book_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_book, key, value)
        db.commit()
        db.refresh(db_book)
    return db_book


def delete_book(db: Session, book_id: int):
    """Удаление книги"""
    db_book = get_book(db, book_id)
    if db_book:
        db.delete(db_book)
        db.commit()
        return True
    return False


def create_loan(db: Session, user_id: int, book_id: int):
    """Создание новой выдачи книги"""
    book = get_book(db, book_id)
    if not book or book.available_copies <= 0:
        return None

    due_date = datetime.utcnow() + timedelta(days=14)

    db_loan = models.Loan(
        user_id=user_id,
        book_id=book_id,
        due_date=due_date
    )

    book.available_copies -= 1

    db.add(db_loan)
    db.commit()
    db.refresh(db_loan)
    return db_loan


def get_active_loan(db: Session, user_id: int, book_id: int):
    """Получение активной выдачи книги пользователю"""
    return db.query(models.Loan).filter(
        models.Loan.user_id == user_id,
        models.Loan.book_id == book_id,
        models.Loan.status == "active"
    ).first()


def get_user_active_loans(db: Session, user_id: int):
    """Получение всех активных выдач пользователя"""
    return db.query(models.Loan).filter(
        models.Loan.user_id == user_id,
        models.Loan.status == "active"
    ).all()


def get_user_loan_history(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """Получение истории выдач пользователя"""
    return db.query(models.Loan).filter(
        models.Loan.user_id == user_id,
        models.Loan.status == "returned"
    ).offset(skip).limit(limit).all()


def return_loan(db: Session, loan_id: int, rating_score: int = None):
    """Возврат книги с возможностью оценки"""
    db_loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
    if not db_loan or db_loan.status != "active":
        return None

    db_loan.return_date = datetime.utcnow()
    db_loan.status = "returned"

    book = get_book(db, db_loan.book_id)
    if book:
        book.available_copies += 1

    if rating_score:
        db_rating = models.Rating(
            user_id=db_loan.user_id,
            book_id=db_loan.book_id,
            score=rating_score
        )
        db.add(db_rating)

    db.commit()
    db.refresh(db_loan)
    return db_loan


def get_book_avg_rating(db: Session, book_id: int):
    """Получение среднего рейтинга книги"""
    result = db.query(func.avg(models.Rating.score)).filter(
        models.Rating.book_id == book_id
    ).first()
    return round(result[0], 2) if result[0] else 0


def get_user_rated_books(db: Session, user_id: int):
    """Получение списка книг, оцененных пользователем"""
    ratings = db.query(models.Rating).filter(models.Rating.user_id == user_id).all()
    return [rating.book_id for rating in ratings]


def get_loan_by_id(db: Session, loan_id: int):
    """Получение выдачи по ID"""
    return db.query(models.Loan).filter(models.Loan.id == loan_id).first()


def get_all_loans(db: Session, skip: int = 0, limit: int = 100, status_filter: str = None):
    """Получение всех выдачей с фильтрацией по статусу"""
    query = db.query(models.Loan)
    if status_filter:
        query = query.filter(models.Loan.status == status_filter)
    return query.offset(skip).limit(limit).all()