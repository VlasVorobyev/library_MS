import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app import models
from app.auth import get_password_hash
import tempfile
import os


@pytest.fixture(scope="session")
def test_engine():
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    test_db_url = f"sqlite:///{temp_db.name}"
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    try:
        os.unlink(temp_db.name)
    except PermissionError:
        pass


@pytest.fixture
def db_session(test_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()

    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        admin_user = models.User(
            username="admin",
            email="admin@library.com",
            hashed_password=get_password_hash("admin123"),
            role="admin"
        )
        db.add(admin_user)
        db.commit()

    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(client):
    response = client.post("/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    return response.json()["access_token"]


@pytest.fixture
def user_token(client):
    client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "pass123"
    })
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "pass123"
    })
    return response.json()["access_token"]


@pytest.fixture
def test_book(admin_token, client):
    response = client.post(
        "/books",
        json={
            "title": "Test Book",
            "author": "Test Author",
            "genre": "Fiction",
            "year": 2024,
            "total_copies": 5
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    return response.json()


class TestAuth:

    def test_register(self, client):
        response = client.post("/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "pass123"
        })
        assert response.status_code == 201
        assert response.json()["role"] == "user"

    def test_register_duplicate_username(self, client):
        client.post("/auth/register", json={
            "username": "duplicate", "email": "dup1@example.com", "password": "pass123"
        })
        response = client.post("/auth/register", json={
            "username": "duplicate", "email": "dup2@example.com", "password": "pass123"
        })
        assert response.status_code == 400

    def test_register_duplicate_email(self, client):
        client.post("/auth/register", json={
            "username": "user1", "email": "same@example.com", "password": "pass123"
        })
        response = client.post("/auth/register", json={
            "username": "user2", "email": "same@example.com", "password": "pass123"
        })
        assert response.status_code == 400

    def test_login_success(self, client):
        client.post("/auth/register", json={
            "username": "loginuser", "email": "login@example.com", "password": "pass123"
        })
        response = client.post("/auth/login", json={
            "username": "loginuser", "password": "pass123"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_invalid_credentials(self, client):
        response = client.post("/auth/login", json={
            "username": "nonexistent", "password": "wrong"
        })
        assert response.status_code == 401


class TestBooks:

    def test_create_book_as_admin(self, admin_token, client):
        response = client.post(
            "/books",
            json={"title": "New Book", "author": "Author", "genre": "Genre", "year": 2024, "total_copies": 3},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 201

    def test_create_book_as_user_forbidden(self, user_token, client):
        response = client.post(
            "/books",
            json={"title": "Hacked", "author": "Hacker", "genre": "Hack", "year": 2024, "total_copies": 1},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403

    def test_create_book_unauthorized(self, client):
        response = client.post("/books", json={"title": "No Auth", "author": "No", "genre": "No", "year": 2024,
                                               "total_copies": 1})
        assert response.status_code == 401

    def test_get_books(self, user_token, client):
        response = client.get("/books", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_book_by_id(self, user_token, client, test_book):
        response = client.get(f"/books/{test_book['id']}", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 200
        assert response.json()["id"] == test_book["id"]

    def test_get_nonexistent_book(self, user_token, client):
        response = client.get("/books/99999", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 404

    def test_update_book_as_admin(self, admin_token, client, test_book):
        response = client.put(
            f"/books/{test_book['id']}",
            json={"title": "Updated", "author": "Updated", "genre": "Updated", "year": 2023, "total_copies": 10},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated"

    def test_update_book_as_user_forbidden(self, user_token, client, test_book):
        response = client.put(
            f"/books/{test_book['id']}",
            json={"title": "Hacked"},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403

    def test_delete_book_as_admin(self, admin_token, client):
        create_response = client.post(
            "/books",
            json={"title": "To Delete", "author": "Temp", "genre": "Temp", "year": 2024, "total_copies": 1},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        book_id = create_response.json()["id"]
        response = client.delete(f"/books/{book_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200

    def test_delete_nonexistent_book(self, admin_token, client):
        response = client.delete("/books/99999", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 404


class TestLoans:

    def test_borrow_book(self, user_token, client, test_book):
        response = client.post(f"/loans/borrow/{test_book['id']}", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 201
        assert response.json()["status"] == "active"

    def test_borrow_unavailable_book(self, user_token, admin_token, client):
        create_response = client.post(
            "/books",
            json={"title": "Single Copy", "author": "Test", "genre": "Test", "year": 2024, "total_copies": 1},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        book_id = create_response.json()["id"]
        client.post(f"/loans/borrow/{book_id}", headers={"Authorization": f"Bearer {user_token}"})
        response = client.post(f"/loans/borrow/{book_id}", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 400

    def test_borrow_same_book_twice(self, user_token, client, test_book):
        client.post(f"/loans/borrow/{test_book['id']}", headers={"Authorization": f"Bearer {user_token}"})
        response = client.post(f"/loans/borrow/{test_book['id']}", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 400

    def test_get_active_loans(self, user_token, client, test_book):
        client.post(f"/loans/borrow/{test_book['id']}", headers={"Authorization": f"Bearer {user_token}"})
        response = client.get("/users/me/loans/active", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 200
        assert len(response.json()) > 0

    def test_return_book_with_rating(self, user_token, client, test_book):
        borrow_response = client.post(f"/loans/borrow/{test_book['id']}",
                                      headers={"Authorization": f"Bearer {user_token}"})
        loan_id = borrow_response.json()["id"]
        response = client.post(f"/loans/return/{loan_id}", json={"rating": 5},
                               headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 200
        assert response.json()["status"] == "returned"

    def test_get_loan_history(self, user_token, client, test_book):
        borrow_response = client.post(f"/loans/borrow/{test_book['id']}",
                                      headers={"Authorization": f"Bearer {user_token}"})
        loan_id = borrow_response.json()["id"]
        client.post(f"/loans/return/{loan_id}", json={"rating": 4}, headers={"Authorization": f"Bearer {user_token}"})
        response = client.get("/users/me/loans/history", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 200


class TestRecommendations:

    def test_get_recommendations(self, admin_token, client):
        response = client.get("/recommendations/for-me", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_similar_books(self, admin_token, client):
        response = client.get("/recommendations/similar-to/1", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code in [200, 404]

    def test_popular_books(self, admin_token, client):
        response = client.get("/stats/popular-books", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_book_rating(self, admin_token, client, test_book):
        response = client.get(f"/books/{test_book['id']}/rating", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        assert "average_rating" in response.json()


class TestUserProfile:

    def test_get_user_me(self, user_token, client):
        response = client.get("/users/me", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 200
        assert response.json()["username"] == "testuser"


class TestAdminFunctions:

    def test_admin_get_all_users(self, admin_token, client):
        response = client.get("/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_non_admin_cannot_get_users(self, user_token, client):
        response = client.get("/admin/users", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--cov=app", "--cov-report=term"])