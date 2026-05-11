from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Book, Rating, Loan
from app.crud import get_book_avg_rating
from typing import List, Dict, Tuple
import math


def calculate_genre_similarity(genre1: str, genre2: str) -> float:
    return 1.0 if genre1 == genre2 else 0.3


def calculate_popularity_score(db: Session, book_id: int) -> float:
    loan_count = db.query(Loan).filter(
        Loan.book_id == book_id,
        Loan.status == "returned"
    ).count()

    avg_rating = get_book_avg_rating(db, book_id)

    if loan_count == 0:
        return 0

    popularity = (loan_count * 0.6) + (avg_rating * 0.4)
    return round(popularity, 2)


def get_user_reading_preferences(db: Session, user_id: int) -> Dict[str, float]:
    user_ratings = db.query(Rating).filter(Rating.user_id == user_id).all()

    if not user_ratings:
        return {}

    genre_scores = {}

    for rating in user_ratings:
        book = db.query(Book).filter(Book.id == rating.book_id).first()
        if book:
            if book.genre not in genre_scores:
                genre_scores[book.genre] = 0
            genre_scores[book.genre] += rating.score

    total_score = sum(genre_scores.values())
    if total_score > 0:
        for genre in genre_scores:
            genre_scores[genre] = round(genre_scores[genre] / total_score, 3)

    return genre_scores


def get_collaborative_recommendations(db: Session, user_id: int, limit: int = 10) -> List[Tuple[int, float]]:
    user_ratings = db.query(Rating).filter(Rating.user_id == user_id).all()
    user_books = set(r.book_id for r in user_ratings)

    other_users = db.query(Rating.user_id).distinct().filter(
        Rating.user_id != user_id
    ).all()

    similarities = []

    for other_user_id in other_users:
        other_ratings = db.query(Rating).filter(Rating.user_id == other_user_id[0]).all()
        other_books = set(r.book_id for r in other_ratings)

        common_books = user_books.intersection(other_books)

        if len(common_books) > 0:
            similarity = len(common_books) / (len(user_books) + len(other_books) - len(common_books))
            similarities.append((other_user_id[0], similarity))

    similarities.sort(key=lambda x: x[1], reverse=True)
    top_similar_users = [u[0] for u in similarities[:5]]

    recommendations = {}

    for other_user_id in top_similar_users:
        other_ratings = db.query(Rating).filter(Rating.user_id == other_user_id).all()
        for rating in other_ratings:
            if rating.book_id not in user_books:
                if rating.book_id not in recommendations:
                    recommendations[rating.book_id] = 0
                recommendations[rating.book_id] += rating.score

    sorted_recommendations = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)
    return sorted_recommendations[:limit]


def get_content_based_recommendations(db: Session, user_id: int, limit: int = 10) -> List[Tuple[int, float]]:
    preferences = get_user_reading_preferences(db, user_id)

    if not preferences:
        return []

    all_books = db.query(Book).all()
    user_rated_books = set(r.book_id for r in db.query(Rating).filter(Rating.user_id == user_id).all())

    recommendations = []

    for book in all_books:
        if book.id in user_rated_books:
            continue

        similarity = preferences.get(book.genre, 0)

        if similarity > 0:
            popularity = calculate_popularity_score(db, book.id)
            total_score = (similarity * 0.7) + (popularity / 10 * 0.3)
            recommendations.append((book.id, round(total_score, 4)))

    recommendations.sort(key=lambda x: x[1], reverse=True)
    return recommendations[:limit]


def get_hybrid_recommendations(db: Session, user_id: int, limit: int = 10) -> List[Dict]:
    content_recs = get_content_based_recommendations(db, user_id, limit)
    collab_recs = get_collaborative_recommendations(db, user_id, limit)

    content_dict = {book_id: score for book_id, score in content_recs}
    collab_dict = {book_id: score for book_id, score in collab_recs}

    all_book_ids = set(content_dict.keys()) | set(collab_dict.keys())

    recommendations = []

    for book_id in all_book_ids:
        content_score = content_dict.get(book_id, 0)
        collab_score = collab_dict.get(book_id, 0)

        hybrid_score = (content_score * 0.6) + (collab_score * 0.4 * 10)
        hybrid_score = round(min(hybrid_score, 1.0), 4)

        recommendations.append((book_id, hybrid_score))

    recommendations.sort(key=lambda x: x[1], reverse=True)

    result = []
    for book_id, score in recommendations[:limit]:
        book = db.query(Book).filter(Book.id == book_id).first()
        if book:
            avg_rating = get_book_avg_rating(db, book_id)
            result.append({
                "book_id": book_id,
                "title": book.title,
                "author": book.author,
                "genre": book.genre,
                "year": book.year,
                "similarity_score": round(score, 3),
                "avg_rating": avg_rating
            })

    return result


def get_similar_books(db: Session, book_id: int, limit: int = 5) -> List[Dict]:
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return []

    similar_books = db.query(Book).filter(
        Book.genre == book.genre,
        Book.id != book_id
    ).all()

    results = []
    for similar in similar_books[:limit]:
        avg_rating = get_book_avg_rating(db, similar.id)
        results.append({
            "book_id": similar.id,
            "title": similar.title,
            "author": similar.author,
            "genre": similar.genre,
            "year": similar.year,
            "similarity_score": 0.8 if similar.author == book.author else 0.5,
            "avg_rating": avg_rating
        })

    return results