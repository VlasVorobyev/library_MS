from typing import List

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import engine, get_db, Base
from app import models, schemas, auth, crud, recommendation

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Library Management System",
    description=" ",
    version="1.0.0"
)


@app.on_event("startup")
def create_default_admin():
    """Создание администратора при запуске приложения"""
    db = next(get_db())
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        hashed_password = auth.get_password_hash("admin123")
        admin_user = models.User(
            username="admin",
            email="admin@library.com",
            hashed_password=hashed_password,
            role="admin"
        )
        db.add(admin_user)
        db.commit()
        print("Admin user created: username=admin, password=admin123")


# ==================== АУТЕНТИФИКАЦИЯ ====================

@app.post("/auth/register", response_model=schemas.UserResponse,
          status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    db_user_by_username = crud.get_user_by_username(db, username=user.username)
    if db_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    db_user_by_email = crud.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = auth.get_password_hash(user.password)
    return crud.create_user(db=db, user=user, hashed_password=hashed_password)


@app.post("/auth/login", response_model=schemas.Token)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    """Вход пользователя, возвращает JWT токен"""
    db_user = auth.authenticate_user(db, user.username, user.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    access_token = auth.create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# ==================== ПОЛЬЗОВАТЕЛИ ====================

@app.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    """Получение информации о текущем пользователе"""
    return current_user


@app.get("/users/me/loans/active", response_model=List[schemas.LoanResponse])
def get_my_active_loans(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Получение списка активных выдач текущего пользователя"""
    return crud.get_user_active_loans(db, current_user.id)


@app.get("/users/me/loans/history", response_model=List[schemas.LoanResponse])
def get_my_loan_history(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Получение истории выдач текущего пользователя"""
    return crud.get_user_loan_history(db, current_user.id, skip, limit)


# ==================== КНИГИ (ТОЛЬКО ДЛЯ АДМИНОВ) ====================

@app.post("/books", response_model=schemas.BookResponse,
          status_code=status.HTTP_201_CREATED)
def create_book(
        book: schemas.BookCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Создание новой книги (только для администратора)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin rights required to create books."
        )
    return crud.create_book(db=db, book=book)


@app.get("/books", response_model=List[schemas.BookResponse])
def get_books(
        skip: int = 0,
        limit: int = 100,
        genre: str = None,
        db: Session = Depends(get_db),
        _current_user: models.User = Depends(auth.get_current_user)
):
    """Получение списка всех книг с возможностью фильтрации по жанру"""
    if genre:
        return crud.get_books_by_genre(db, genre, skip, limit)
    return crud.get_all_books(db, skip, limit)


@app.get("/books/{book_id}", response_model=schemas.BookResponse)
def get_book(
        book_id: int,
        db: Session = Depends(get_db),
        _current_user: models.User = Depends(auth.get_current_user)
):
    """Получение информации о конкретной книге по ID"""
    db_book = crud.get_book(db, book_id)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return db_book


@app.put("/books/{book_id}", response_model=schemas.BookResponse)
def update_book(
        book_id: int,
        book: schemas.BookUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Обновление информации о книге (только для администратора)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin rights required to update books."
        )
    db_book = crud.update_book(db, book_id, book)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return db_book


@app.delete("/books/{book_id}", status_code=status.HTTP_200_OK)
def delete_book(
        book_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Удаление книги (только для администратора)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin rights required to delete books."
        )

    active_loans = db.query(models.Loan).filter(
        models.Loan.book_id == book_id,
        models.Loan.status == "active"
    ).first()

    if active_loans:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete book with active loans. "
                   "Please wait for all copies to be returned."
        )

    success = crud.delete_book(db, book_id)
    if not success:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"message": "Book deleted successfully"}


# ==================== ВЫДАЧА КНИГ ====================

@app.post("/loans/borrow/{book_id}", response_model=schemas.LoanResponse,
          status_code=status.HTTP_201_CREATED)
def borrow_book(
        book_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Выдача книги пользователю"""
    active_loans = crud.get_user_active_loans(db, current_user.id)
    if len(active_loans) >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have reached the maximum number of active loans (5)"
        )

    existing_loan = crud.get_active_loan(db, current_user.id, book_id)
    if existing_loan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have this book borrowed"
        )

    db_loan = crud.create_loan(db, current_user.id, book_id)
    if db_loan is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book is not available for borrowing"
        )

    return db_loan


@app.post("/loans/return/{loan_id}", response_model=schemas.LoanResponse)
def return_book(
        loan_id: int,
        return_data: schemas.LoanReturn = None,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Возврат книги с возможностью оценки"""
    db_loan = crud.get_loan_by_id(db, loan_id)
    if db_loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")

    if db_loan.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot return another user's book. Admin rights required."
        )

    rating = return_data.rating if return_data else None
    db_loan = crud.return_loan(db, loan_id, rating)
    if db_loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")

    return db_loan


# ==================== АДМИН-ФУНКЦИИ ====================

@app.get("/admin/loans", response_model=List[schemas.LoanResponse])
def get_all_loans(
        skip: int = 0,
        limit: int = 100,
        status_filter: str = None,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Получение всех выдач (только для администратора)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin rights required."
        )
    return crud.get_all_loans(db, skip, limit, status_filter)


@app.get("/admin/users", response_model=List[schemas.UserResponse])
def get_all_users(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Получение всех пользователей (только для администратора)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin rights required."
        )
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users


@app.put("/admin/users/{user_id}/role")
def change_user_role(
        user_id: int,
        role: str,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Изменение роли пользователя (только для администратора)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin rights required."
        )

    if role not in ["user", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'user' or 'admin'"
        )

    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role"
        )

    user.role = role
    db.commit()
    db.refresh(user)

    return {"message": f"User {user.username} role changed to {role}"}


# ==================== РЕКОМЕНДАЦИИ ====================

@app.get("/recommendations/for-me", response_model=List[schemas.BookRecommendation])
def get_recommendations_for_me(
        limit: int = 10,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    """Получение персональных рекомендаций книг"""
    user_ratings_count = db.query(models.Rating).filter(
        models.Rating.user_id == current_user.id
    ).count()

    if user_ratings_count < 3:
        popular_books = crud.get_all_books(db, limit=limit)
        return [
            {
                "book_id": book.id,
                "title": book.title,
                "author": book.author,
                "genre": book.genre,
                "year": book.year,
                "similarity_score": 0.5,
                "avg_rating": crud.get_book_avg_rating(db, book.id)
            }
            for book in popular_books
        ]

    return recommendation.get_hybrid_recommendations(db, current_user.id, limit)


@app.get("/recommendations/similar-to/{book_id}", response_model=List[schemas.BookRecommendation])
def get_similar_books(
        book_id: int,
        limit: int = 5,
        db: Session = Depends(get_db),
        _current_user: models.User = Depends(auth.get_current_user)
):
    """Получение книг, похожих на указанную"""
    book = crud.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return recommendation.get_similar_books(db, book_id, limit)


# ==================== СТАТИСТИКА ====================

@app.get("/stats/popular-books", response_model=List[schemas.BookRecommendation])
def get_popular_books(
        limit: int = 10,
        db: Session = Depends(get_db),
        _current_user: models.User = Depends(auth.get_current_user)
):
    """Получение списка популярных книг"""
    all_books = crud.get_all_books(db, limit=50)

    popular_books = []
    for book in all_books:
        popularity = recommendation.calculate_popularity_score(db, book.id)
        avg_rating = crud.get_book_avg_rating(db, book.id)
        popular_books.append({
            "book_id": book.id,
            "title": book.title,
            "author": book.author,
            "genre": book.genre,
            "year": book.year,
            "similarity_score": popularity / 10,
            "avg_rating": avg_rating
        })

    popular_books.sort(key=lambda x: x["similarity_score"], reverse=True)
    return popular_books[:limit]


@app.get("/books/{book_id}/rating")
def get_book_rating(
        book_id: int,
        db: Session = Depends(get_db),
        _current_user: models.User = Depends(auth.get_current_user)
):
    """Получение рейтинга книги"""
    book = crud.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    avg_rating = crud.get_book_avg_rating(db, book_id)
    rating_count = db.query(models.Rating).filter(
        models.Rating.book_id == book_id
    ).count()

    return {
        "book_id": book_id,
        "title": book.title,
        "average_rating": avg_rating,
        "ratings_count": rating_count
    }
